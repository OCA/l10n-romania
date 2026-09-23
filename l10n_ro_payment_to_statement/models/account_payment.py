# Copyright (C) 2015-2020 Deltatech
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _name = "account.payment"
    _inherit = ["account.payment", "l10n.ro.mixin"]

    l10n_ro_statement_id = fields.Many2one(
        "account.bank.statement",
        string="Romania - Statement",
        domain="[('journal_id','=',journal_id)]",
    )

    l10n_ro_statement_line_id = fields.Many2one(
        "account.bank.statement.line",
        string="Statement Line",
        readonly=True,
        domain="[('l10n_ro_statement_id','=',statement_id)]",
    )

    def _l10n_ro_is_auto_statement(self):
        """Payment kept in an automatic cash register (registru de casa)."""
        self.ensure_one()
        return (
            self.is_l10n_ro_record
            and self.journal_id.type == "cash"
            and self.journal_id.l10n_ro_auto_statement
        )

    def _l10n_ro_check_register_account(self):
        """The register needs an account of its own to bring the money in.

        The line of the register moves the money from the account of the
        payment method into the cash account (5311 = 581). With the cash
        account on both sides there is no movement to register.
        """
        self.ensure_one()
        if self.outstanding_account_id and (
            self.outstanding_account_id != self.journal_id.default_account_id
        ):
            return
        raise UserError(
            self.env._(
                "The journal %(journal)s keeps a cash register, so the payment "
                "method %(method)s needs an outstanding account of its own, "
                "other than the cash account %(cash)s of the journal. The "
                "register line brings the money from that account into the "
                "cash one, and there is nothing to bring in otherwise.",
                journal=self.journal_id.display_name,
                method=self.payment_method_line_id.display_name,
                cash=self.journal_id.default_account_id.display_name,
            )
        )

    def _l10n_ro_get_statement_line(self):
        """Cash register line of this payment, however it was built."""
        self.ensure_one()
        return self.l10n_ro_statement_line_id or self.reconciled_statement_line_ids

    def _l10n_ro_add_to_statement(self):
        """Add the payment to the cash register of its day.

        The payment and its register line are two entries: the payment moves
        the money to the account of its payment method (4111 = 581), the
        register line brings it into the cash account (5311 = 581), and the
        two are reconciled with each other, so nothing is left to match by
        hand.
        """
        self.ensure_one()
        if not self.move_id:
            return
        lines = self._l10n_ro_get_statement_line()
        if lines:
            if all(line._l10n_ro_stands_for(self) for line in lines):
                # the payment may have been posted again on another day
                lines._l10n_ro_move_to_statement_of_the_day()
                self.l10n_ro_statement_id = lines[:1].statement_id
                return
            # posted again with other values: the line is remade below
            lines._l10n_ro_drop()
        statement = self.env["account.bank.statement"]._l10n_ro_get_statement(
            self.journal_id, self.date
        )
        self._l10n_ro_create_statement_line(statement)

    def _l10n_ro_prepare_statement_line(self, statement):
        self.ensure_one()
        return {
            "statement_id": statement.id,
            "journal_id": self.journal_id.id,
            "date": self.date,
            "partner_id": self.partner_id.id,
            "payment_ref": self.payment_reference or self.name,
            "amount": -self.amount if self.payment_type == "outbound" else self.amount,
        }

    def _l10n_ro_create_statement_line(self, statement):
        """Add a register line for the money coming from the outstanding account."""
        self.ensure_one()
        invoices = self.reconciled_invoice_ids | self.reconciled_bill_ids
        line = self.env["account.bank.statement.line"].create(
            dict(
                self._l10n_ro_prepare_statement_line(statement),
                ref=", ".join(invoices.mapped("name")),
                counterpart_account_id=self.outstanding_account_id.id,
            )
        )
        if self.outstanding_account_id.reconcile:
            outstanding_lines = (
                line.move_id.line_ids | self.move_id.line_ids
            ).filtered(
                lambda aml: aml.account_id == self.outstanding_account_id
                and not aml.reconciled
            )
            outstanding_lines.reconcile()
        self.write(
            {
                "l10n_ro_statement_id": statement.id,
                "l10n_ro_statement_line_id": line.id,
            }
        )
        return line

    def action_post(self):
        kept_in_a_register = self.filtered(
            lambda payment: payment._l10n_ro_is_auto_statement()
        )
        for payment in kept_in_a_register:
            payment._l10n_ro_check_register_account()
        res = super().action_post()
        for payment in kept_in_a_register:
            payment._l10n_ro_add_to_statement()
        return res

    def _l10n_ro_drop_statement_line(self):
        """Take out the register line this module made for the payment.

        Only that one: a payment can also be reconciled with lines which
        came from the bank, and those are none of our business.
        """
        for payment in self:
            if payment._l10n_ro_is_auto_statement():
                payment.l10n_ro_statement_line_id._l10n_ro_drop()

    def action_cancel(self):
        # the register line is an entry of its own, it does not follow the
        # payment by itself
        self._l10n_ro_drop_statement_line()
        return super().action_cancel()

    def action_draft(self):
        self._l10n_ro_drop_statement_line()
        return super().action_draft()

    def l10n_ro_force_cash_sequence(self):
        # force cash in/out sequence. Called from related account move
        for payment in self:
            cash_sequence = payment.move_id.with_context(
                l10n_ro_payment_type=payment.payment_type,
                l10n_ro_partner_type=payment.partner_type,
            ).get_l10n_ro_sequence()
            if cash_sequence:
                payment.name = cash_sequence.next_by_id()
                if payment.move_id:
                    payment.move_id.name = payment.name

    def unlink(self):
        # the register line shares, or is reconciled with, the entry of the
        # payment, so it goes away with it
        self._check_can_unlink()
        return super().unlink()

    def _check_can_unlink(self):
        for payment in self:
            # forbid deleting if has a number
            if (
                payment.is_l10n_ro_record
                and payment.name
                and payment.name != "/"
                and payment.journal_id.type == "cash"
            ):
                raise UserError(
                    self.env._(
                        "You cannot delete the payment %s, "
                        "as it already consumed a number.",
                        payment.display_name,
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        res = self.env["account.payment"]
        for vals in vals_list:
            new_context = dict(self.env.context)
            new_context.pop("l10n_ro_payment_type", None)
            new_context.pop("l10n_ro_partner_type", None)
            if vals.get("payment_type"):
                new_context["l10n_ro_payment_type"] = vals.get("payment_type")
            if vals.get("partner_type"):
                new_context["l10n_ro_partner_type"] = vals.get("partner_type")
            self = self.with_context(**new_context)
            payment = super().create([vals])
            res |= payment
        return res
