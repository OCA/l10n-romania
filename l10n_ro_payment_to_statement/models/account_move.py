# Copyright (C) 2015-2020 Deltatech
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    def _constrains_date_sequence(self):
        l10n_ro_record = self.filtered("is_l10n_ro_record")
        l10n_ro_not_record = self - l10n_ro_record
        if l10n_ro_not_record:
            return super(AccountMove, l10n_ro_not_record)._constrains_date_sequence()
        if (
            l10n_ro_record
            and not self.journal_id.l10n_ro_journal_sequence_id
            and self.journal_id.type != "cash"
        ):
            return super(AccountMove, l10n_ro_record)._constrains_date_sequence()

    def _set_next_sequence(self):
        self.ensure_one()
        l10n_ro_record = self.filtered("is_l10n_ro_record")
        l10n_ro_not_record = self - l10n_ro_record
        if l10n_ro_not_record:
            return super(AccountMove, l10n_ro_not_record)._set_next_sequence()
        if (
            l10n_ro_record
            and self.journal_id.l10n_ro_journal_sequence_id
            and self.journal_id.type == "cash"
        ):
            last_sequence = self._get_last_sequence()
            new = not last_sequence
            if new:
                last_sequence = (
                    self._get_last_sequence(relaxed=True)
                    or self._get_starting_sequence()
                )
            format, format_values = self._get_sequence_format_param(last_sequence)
            new_number = ""
            if new:
                if self.journal_id.l10n_ro_journal_sequence_id:
                    new_number = (
                        self.journal_id.l10n_ro_journal_sequence_id.next_by_id()
                    )
                format_values["seq"] = 0
                format_values["year"] = self[self._sequence_date_field].year % (
                    10 ** format_values["year_length"]
                )
                format_values["month"] = self[self._sequence_date_field].month
            format_values["seq"] = format_values["seq"] + 1
            if not new_number:
                self[self._sequence_field] = format.format(**format_values)
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
            if move.payment_id and move.is_l10n_ro_record:
                move.payment_id.l10n_ro_force_cash_sequence()
        return super()._post(soft)
