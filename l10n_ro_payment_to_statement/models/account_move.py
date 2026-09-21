# Copyright (C) 2015-2020 Deltatech
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    def get_l10n_ro_sequence(self):
        """Sequence giving the number of a Romanian cash entry."""
        self.ensure_one()
        if self.origin_payment_id:
            self = self.with_context(
                l10n_ro_payment_type=self.origin_payment_id.payment_type,
                l10n_ro_partner_type=self.origin_payment_id.partner_type,
            )
        if not (
            self.origin_payment_id
            and self.is_l10n_ro_record
            and self.journal_id.type == "cash"
        ):
            return self.journal_id.l10n_ro_journal_sequence_id

        partner_type = self.env.context.get("l10n_ro_partner_type", "")
        payment_type = self.env.context.get("l10n_ro_payment_type", "")
        sequences = {
            (
                "customer",
                "inbound",
            ): self.journal_id.l10n_ro_customer_cash_in_sequence_id,
            ("customer", "outbound"): self.journal_id.l10n_ro_cash_out_sequence_id,
            ("supplier", "inbound"): self.journal_id.l10n_ro_cash_in_sequence_id,
            ("supplier", "outbound"): self.journal_id.l10n_ro_journal_sequence_id,
        }
        return sequences.get(
            (partner_type, payment_type), self.journal_id.l10n_ro_journal_sequence_id
        )

    def _l10n_ro_is_first_entry(self):
        """No entry of this kind in the database yet."""
        self.ensure_one()
        last_sequence = (
            self._get_last_sequence(relaxed=True) or self._get_starting_sequence()
        )
        _format, format_values = self._get_sequence_format_param(last_sequence)
        return format_values["seq"] == 0

    def _set_next_sequence(self):
        self.ensure_one()
        cash_sequence = self.get_l10n_ro_sequence()
        if not cash_sequence:
            return super()._set_next_sequence()
        if self.origin_payment_id:
            # the number of a receipt is taken when its payment is posted, see
            # _l10n_ro_consume_cash_sequence and l10n_ro_force_cash_sequence
            return

        if self._l10n_ro_is_first_entry():
            # only read the number: a create() which is then discarded must
            # not consume it. It is taken when the entry is posted.
            self[self._sequence_field] = cash_sequence.get_next_char(
                cash_sequence.number_next_actual
            )
        else:
            self[self._sequence_field] = cash_sequence.next_by_id()
        self._compute_split_sequence()

    def _l10n_ro_consume_cash_sequence(self):
        """Give a posted cash entry the number of its Romanian sequence."""
        for move in self.filtered("is_l10n_ro_record"):
            cash_sequence = move.get_l10n_ro_sequence()
            if not cash_sequence or (
                move.origin_payment_id and move.origin_payment_id.state != "in_process"
            ):
                continue
            if not move.name or move.name == "/":
                move.name = cash_sequence.next_by_id()
            elif not move._get_last_sequence():
                # _set_next_sequence only read the number of the first entry,
                # posting it is what consumes it
                cash_sequence.next_by_id()

    def _l10n_ro_set_disposal_name(self, statement_line):
        """Number a cash in/out slip made straight in the cash register."""
        for move in self:
            if move.name and move.name != "/":
                continue
            if statement_line.amount >= 0.0:
                sequence = move.journal_id.l10n_ro_cash_in_sequence_id
            else:
                sequence = move.journal_id.l10n_ro_cash_out_sequence_id
            if sequence:
                move.name = sequence.next_by_id()

    def write(self, vals):
        if vals.get("state") == "posted" and not vals.get("name"):
            self._l10n_ro_consume_cash_sequence()
        if vals.get("statement_line_id") and not vals.get("name"):
            statement_line = self.env["account.bank.statement.line"].browse(
                vals["statement_line_id"]
            )
            if statement_line.is_l10n_ro_payment_disposal:
                self._l10n_ro_set_disposal_name(statement_line)
        return super().write(vals)

    def action_post(self):
        if self.env.context.get("is_statement_line"):
            # a register line can be created on the entry of a payment, which
            # is already posted
            self = self.filtered(lambda move: move.state == "draft")
        return super().action_post()

    def _post(self, soft=True):
        for move in self.filtered("is_l10n_ro_record"):
            if (
                move.origin_payment_id
                and move.origin_payment_id.state != "in_process"
                and (not move.name or move.name == "/")
            ):
                move.origin_payment_id.l10n_ro_force_cash_sequence()

            if (
                move.statement_line_id
                and not move.statement_line_id.statement_id
                and move.journal_id.type == "cash"
                and move.journal_id.l10n_ro_auto_statement
            ):
                # a line made straight in the cash register belongs to the
                # register of its day
                move.statement_line_id.statement_id = self.env[
                    "account.bank.statement"
                ]._l10n_ro_get_statement(move.journal_id, move.date)
        return super()._post(soft)
