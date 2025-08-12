# Copyright (C) 2015-2020 Deltatech
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _name = "account.payment"
    _inherit = ["account.payment", "l10n.ro.mixin"]

    l10n_ro_statement_id = fields.Many2one(
        "account.bank.statement",
        string="Romania - Statement",
        domain="[('journal_id','=',journal_id)]",
    )

    statement_line_id = fields.Many2one(
        "account.bank.statement.line",
        string="Statement Line",
        readonly=True,
        domain="[('l10n_ro_statement_id','=',statement_id)]",
    )

    def get_l10n_ro_statement_line(self):
        lines = self.env["account.bank.statement.line"]
        self.get_l10n_ro_reconciled_statement_line()
        for payment in self:
            auto_statement = payment.journal_id.l10n_ro_auto_statement
            if (
                auto_statement
                and not payment.l10n_ro_statement_id
                and not payment.reconciled_statement_line_ids
            ):
                domain = [
                    ("date", "=", payment.date),
                    ("journal_id", "=", payment.journal_id.id),
                ]
                statement = self.env["account.bank.statement"].search(domain, limit=1)
                if not statement:
                    values = {
                        "journal_id": payment.journal_id.id,
                        "date": payment.date,
                        "name": "/",
                    }
                    statement = payment.env["account.bank.statement"].create(values)
                payment.write({"l10n_ro_statement_id": statement.id})

            if (
                payment.state == "posted"
                and not payment.statement_line_id
                and payment.l10n_ro_statement_id
            ):
                ref = ""
                for invoice in payment.reconciled_bill_ids:
                    ref += invoice.name
                for invoice in payment.reconciled_invoice_ids:
                    ref += invoice.name
                values = {
                    "statement_id": payment.l10n_ro_statement_id.id,
                    "date": payment.date,
                    "partner_id": payment.partner_id.id,
                    "amount": payment.amount,
                    "ref": ref,
                    "payment_ref": payment.ref or payment.name,
                    "journal_id": payment.journal_id.id,
                }
                if payment.payment_type == "outbound":
                    values["amount"] = -1 * payment.amount

                line = payment.env["account.bank.statement.line"].create(values)
                lines |= line
                payment.write({"statement_line_id": line.id})

    def get_l10n_ro_reconciled_statement_line(self):
        for payment in self:
            for move_line in payment.reconciled_statement_line_ids:
                if move_line.statement_id and move_line.statement_line_id:
                    payment.write(
                        {
                            "l10n_ro_statement_id": move_line.statement_id.id,
                            "statement_line_id": move_line.statement_line_id.id,
                        }
                    )

    def action_post(self):
        res = super().action_post()
        l10n_ro_records = self.filtered(lambda p: p.is_l10n_ro_record)
        if l10n_ro_records:
            for payment in l10n_ro_records:
                payment.move_id._get_l10n_ro_bank_statement()
            l10n_ro_records.get_l10n_ro_statement_line()
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

    def unlink(self):
        statement_line_ids = self.env["account.bank.statement.line"]
        for payment in self:
            # forbid deleting if has a number
            if (
                payment.is_l10n_ro_record
                and payment.name
                and payment.name != "/"
                and payment.journal_id.type == "cash"
            ):
                raise UserError(
                    _(
                        "You cannot delete the payment %s,"
                        " as it already consumed a number."
                    )
                    % payment.name
                )
        res = super().unlink()
        statement_line_ids.unlink()
        return res

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
