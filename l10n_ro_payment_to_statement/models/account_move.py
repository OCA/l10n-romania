# Copyright (C) 2015-2020 Deltatech
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    def _get_starting_sequence(self):
        return super()._get_starting_sequence()

    def _get_last_sequence_domain(self, relaxed=False):
        where_string, param = super()._get_last_sequence_domain(relaxed)

        return where_string, param

    def get_l10n_ro_sequence(self):
        self.ensure_one()
        if self.payment_id:
            self = self.with_context(
                l10n_ro_payment_type=self.payment_id.payment_type,
                l10n_ro_partner_type=self.payment_id.partner_type,
            )
        sequence = self.journal_id.l10n_ro_journal_sequence_id
        if (
            self.payment_id
            and self.is_l10n_ro_record
            and self.journal_id.type == "cash"
        ):
            partner_type = self._context.get("l10n_ro_partner_type", "")
            payment_type = self._context.get("l10n_ro_payment_type", "")
            if partner_type == "customer":
                if payment_type == "inbound":
                    sequence = self.journal_id.l10n_ro_customer_cash_in_sequence_id
                if payment_type == "outbound":
                    sequence = self.journal_id.l10n_ro_cash_out_sequence_id
            if partner_type == "supplier":
                if payment_type == "inbound":
                    sequence = self.journal_id.l10n_ro_cash_in_sequence_id
                if payment_type == "outbound":
                    sequence = self.journal_id.l10n_ro_journal_sequence_id
        return sequence

    def _set_next_sequence(self):
        self.ensure_one()
        cash_sequence = self.get_l10n_ro_sequence()
        if cash_sequence:
            last_sequence = (
                self._get_last_sequence(relaxed=True) or self._get_starting_sequence()
            )
            format_seq, format_values = self._get_sequence_format_param(last_sequence)
            if not self.payment_id:
                if format_values["seq"] != 0:
                    new_number = cash_sequence.next_by_id()
                else:
                    # aici sunt in cazul in care s-a dat create(),
                    # insa nu exista nimic in baza de date
                    # deci vreau doar sa citesc ultima valoare din secventa,
                    #
                    # nu incrementez deoarece daca se da discard, nu vreau sa
                    # se incrementeze secventa
                    new_number = cash_sequence.get_next_char(
                        cash_sequence.number_next_actual
                    )

                self[self._sequence_field] = new_number

                self._compute_split_sequence()
        else:
            return super()._set_next_sequence()

    def write(self, vals):
        if "state" in vals and vals.get("state") == "posted":
            for move in self:
                if move.is_l10n_ro_record:
                    cash_sequence = move.get_l10n_ro_sequence()
                    if cash_sequence and (
                        not move.payment_id or move.payment_id.state == "posted"
                    ):
                        if not move.name or move.name == "/":
                            new_number = cash_sequence.next_by_id()
                            super(AccountMove, move).write({"name": new_number})
                        else:
                            last_sequence = move._get_last_sequence()
                            if not last_sequence:
                                # trebuie incrementata secventa deoarece sunt in cazul
                                # in care nu a existat nici o factura/nota
                                # in baza de date
                                #
                                # si in _set_next_sequence de mai sus new_number
                                # a fost initializat cu
                                # cash_sequence.get_next_char(number_next_actual),
                                #
                                # deci fara sa se dea next_by_id()
                                cash_sequence.next_by_id()

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
        return super().write(vals)

    def _get_l10n_ro_bank_statement(self):
        self.ensure_one()
        domain = [("date", "=", self.date), ("journal_id", "=", self.journal_id.id)]
        statement = self.env["account.bank.statement"].search(domain, limit=1)
        if statement:
            self.payment_id.l10n_ro_statement_id = statement
            self.statement_line_id.statement_id = statement
            lines = statement.line_ids.filtered(lambda x: x.state == "posted")
            balance_end = (
                statement.balance_start
                + sum(lines.mapped("amount"))
                + self.statement_line_id.amount
            )
            statement.write(
                {"balance_end": balance_end, "balance_end_real": balance_end}
            )
        else:
            # daca tipul este numerar trebuie generat
            if self.journal_id.l10n_ro_auto_statement:
                values = {
                    "journal_id": self.journal_id.id,
                    "date": self.date,
                    "name": "/",
                }
                statement = self.env["account.bank.statement"].sudo().create(values)
                self.payment_id.l10n_ro_statement_id = statement
                self.statement_line_id.statement_id = statement
                lines = statement.line_ids.filtered(lambda x: x.state == "posted")
                balance_end = (
                    statement.balance_start
                    + sum(lines.mapped("amount"))
                    + self.statement_line_id.amount
                )
                statement.write(
                    {"balance_end": balance_end, "balance_end_real": balance_end}
                )

    def _post(self, soft=True):
        for move in self:
            if move.is_l10n_ro_record:
                if (
                    move.payment_id
                    and move.payment_id.state != "posted"
                    and (not move.name or move.name == "/")
                ):
                    move.payment_id.l10n_ro_force_cash_sequence()

                if (
                    move.payment_id or move.statement_line_id
                ) and move.journal_id.l10n_ro_auto_statement:
                    move._get_l10n_ro_bank_statement()
        return super()._post(soft)
