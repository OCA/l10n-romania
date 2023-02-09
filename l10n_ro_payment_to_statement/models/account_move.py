# Copyright (C) 2015-2020 Deltatech
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import _, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_date


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    def _constrains_date_sequence(self):
        constraint_date = fields.Date.to_date(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("sequence.mixin.constraint_start_date", "1970-01-01")
        )
        for record in self:
            date = fields.Date.to_date(record[record._sequence_date_field])
            sequence = record[record._sequence_field]
            if sequence and date and date > constraint_date:
                format_values = record._get_sequence_format_param(sequence)[1]
                if (
                    format_values["year"]
                    and format_values["year"]
                    != date.year % 10 ** len(str(format_values["year"]))
                    or format_values["month"]
                    and format_values["month"] != date.month
                ) and not record.journal_id.l10n_ro_journal_sequence_id:
                    raise ValidationError(
                        _(
                            "The %(date_field)s (%(date)s) doesn't match "
                            "the %(sequence_field)s (%(sequence)s).\n"
                            "You might want to clear the field %(sequence_field)s "
                            "before proceeding with the change of the date.",
                            date=format_date(self.env, date),
                            sequence=sequence,
                            date_field=record._fields[
                                record._sequence_date_field
                            ]._description_string(self.env),
                            sequence_field=record._fields[
                                record._sequence_field
                            ]._description_string(self.env),
                        )
                    )

    def _set_next_sequence(self):
        self.ensure_one()
        last_sequence = self._get_last_sequence()
        new = not last_sequence
        if new:
            last_sequence = (
                self._get_last_sequence(relaxed=True) or self._get_starting_sequence()
            )
        format, format_values = self._get_sequence_format_param(last_sequence)
        new_number = ""
        if new:
            if self.journal_id.l10n_ro_journal_sequence_id:
                new_number = self.journal_id.l10n_ro_journal_sequence_id.next_by_id()
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
