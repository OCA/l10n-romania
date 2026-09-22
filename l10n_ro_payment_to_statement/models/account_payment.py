# Copyright (C) 2015-2020 Deltatech
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import Command, api, fields, models
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

    def _l10n_ro_get_statement_line(self):
        """Cash register line of this payment, however it was built."""
        self.ensure_one()
        return (
            self.l10n_ro_statement_line_id
            or self.move_id.statement_line_id
            or self.reconciled_statement_line_ids
        )

    def _l10n_ro_add_to_statement(self):
        """Add the payment to the cash register of its day.

        The account of the payment method decides how the register line is
        built:

        * the cash account of the journal: the entry of the payment already is
          the one of the register (5311 = 4111), so the statement line reuses
          it and no second entry is created;
        * an outstanding account: the money reaches the cash register through a
          transit account (4111 = 581 on the payment, 5311 = 581 on the
          register), so the line gets its own entry, booked against that
          transit account and reconciled with the payment.

        A payment without an account on its payment method has no entry at all,
        so there is nothing to register and no line is created.
        """
        self.ensure_one()
        if not self.move_id:
            return
        lines = self._l10n_ro_get_statement_line()
        if lines:
            # already registered, but the payment may have been posted again
            # on another day
            lines._l10n_ro_move_to_statement_of_the_day()
            if self.l10n_ro_statement_line_id:
                self.l10n_ro_statement_id = self.l10n_ro_statement_line_id.statement_id
            return
        statement = self.env["account.bank.statement"]._l10n_ro_get_statement(
            self.journal_id, self.date
        )
        if self.outstanding_account_id == self.journal_id.default_account_id:
            self._l10n_ro_reuse_move_as_statement_line(statement)
        else:
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

    def _l10n_ro_reuse_move_as_statement_line(self, statement):
        """Turn the entry of the payment into the line of the cash register."""
        self.ensure_one()
        move = self.move_id
        name = move.name
        line = (
            self.env["account.bank.statement.line"]
            .with_context(
                # the entry of the payment is posted, and the statement line is
                # created on it without touching what it already holds
                skip_readonly_check=True
            )
            .create(
                dict(
                    self._l10n_ro_prepare_statement_line(statement),
                    move_id=move.id,
                    # the lines of the payment already are the ones of the register
                    # (cash account and receivable/payable), keep them untouched
                    line_ids=[Command.set(move.line_ids.ids)],
                )
            )
        )
        if move.name != name:
            # creating the line resets the name of the entry to have it
            # recomputed, but the payment already consumed a cash number
            move.write({"name": name})
        # the entry is the one of the payment, there is nothing left to review
        move.checked = True
        self.write(
            {
                "l10n_ro_statement_id": statement.id,
                "l10n_ro_statement_line_id": line.id,
            }
        )
        return line

    def _l10n_ro_create_statement_line(self, statement):
        """Add a register line for the money coming from the transit account."""
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
            transit_lines = (line.move_id.line_ids | self.move_id.line_ids).filtered(
                lambda aml: aml.account_id == self.outstanding_account_id
                and not aml.reconciled
            )
            transit_lines.reconcile()
        self.write(
            {
                "l10n_ro_statement_id": statement.id,
                "l10n_ro_statement_line_id": line.id,
            }
        )
        return line

    def action_post(self):
        res = super().action_post()
        for payment in self:
            if payment._l10n_ro_is_auto_statement():
                payment._l10n_ro_add_to_statement()
        return res

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
