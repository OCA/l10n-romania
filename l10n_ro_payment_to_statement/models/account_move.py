# Copyright (C) 2015-2020 Deltatech
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    def get_l10n_ro_sequence(self):
        self.ensure_one()
        sequence = self.journal_id.l10n_ro_journal_sequence_id
        if self.is_l10n_ro_record and self.journal_id.type == "cash":
            partner_type = self._context.get(
                "l10n_ro_partner_type", self.payment_id.partner_type
            )
            payment_type = self._context.get(
                "l10n_ro_payment_type", self.payment_id.payment_type
            )
            if partner_type == "customer":
                if payment_type == "inbound":
                    sequence = self.journal_id.l10n_ro_customer_cash_in_sequence_id
                if payment_type == "outbound":
                    sequence = self.journal_id.l10n_ro_cash_out_sequence_id

        return sequence

    def _set_next_sequence(self):
        self.ensure_one()
        last_sequence = self._get_last_sequence()
        cash_sequence = self.get_l10n_ro_sequence()
        if cash_sequence and not last_sequence:
            last_sequence = (
                self._get_last_sequence(relaxed=True) or self._get_starting_sequence()
            )
            format_seq, format_values = self._get_sequence_format_param(last_sequence)
            new_number = cash_sequence.next_by_id()
            format_values["seq"] = 1
            format_values["year"] = self[self._sequence_date_field].year % (
                10 ** format_values["year_length"]
            )
            format_values["month"] = self[self._sequence_date_field].month
            if not new_number:
                self[self._sequence_field] = format_seq.format(**format_values)
            else:
                self[self._sequence_field] = new_number
            self._compute_split_sequence()
        else:
            return super(AccountMove, self)._set_next_sequence()

    def write(self, vals):
        if "state" in vals and vals.get("state") == "posted":
            for move in self:
                if move.is_l10n_ro_record:
                    if (
                        not move.name or move.name == "/"
                    ) and move.journal_id.l10n_ro_journal_sequence_id:
                        new_number = (
                            move.journal_id.l10n_ro_journal_sequence_id.next_by_id()
                        )
                        super(AccountMove, move).write({"name": new_number})

        if "statement_line_id" in vals and vals.get("statement_line_id"):
            statement_line = self.env["account.bank.statement.line"].browse(
                vals.get("statement_line_id")
            )
            for move in self:
                if (
                    not move.name
                    or move.name == "/"
                    and statement_line.is_l10n_ro_payment_disposal
                ):
                    if (
                        statement_line.amount >= 0.0
                        and move.journal_id.l10n_ro_cash_in_sequence_id
                    ):
                        new_number = (
                            move.journal_id.l10n_ro_cash_in_sequence_id.next_by_id()
                        )
                        super(AccountMove, move).write({"name": new_number})
                    elif (
                        statement_line.amount < 0.0
                        and move.journal_id.l10n_ro_cash_out_sequence_id
                    ):
                        new_number = (
                            move.journal_id.l10n_ro_cash_out_sequence_id.next_by_id()
                        )
                        super(AccountMove, move).write({"name": new_number})

        return super(AccountMove, self).write(vals)

    def _post(self, soft=True):
        for move in self:
            last_sequence = move._get_last_sequence()
            if last_sequence and move.payment_id and move.is_l10n_ro_record:
                move.payment_id.l10n_ro_force_cash_sequence()
        return super()._post(soft)
