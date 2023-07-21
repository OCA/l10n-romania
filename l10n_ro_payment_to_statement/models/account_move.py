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
            partner_type = self._context.get("l10n_ro_partner_type", "")
            payment_type = self._context.get("l10n_ro_payment_type", "")
            if partner_type == "customer":
                if payment_type == "inbound":
                    sequence = self.journal_id.l10n_ro_customer_cash_in_sequence_id
                if payment_type == "outbound":
                    sequence = self.journal_id.l10n_ro_cash_out_sequence_id

        return sequence

    def _get_last_sequence(self, relaxed=False, lock=True):
        cash_sequence = self.get_l10n_ro_sequence()
        if cash_sequence:
            # acest cod asigura ca se da continue cand se apeleaza din
            #
            # @api.depends('posted_before', 'state', 'journal_id', 'date')
            # def _compute_name(self):
            #    ....
            #
            #   for move in self:
            #       ...
            #        move_has_name = move.name and move.name != '/'
            #        if move_has_name or move.state != 'posted':
            #           try:
            #               ...
            #               if (
            #                   move_has_name and move.posted_before
            #                   or not move_has_name and move._get_last_sequence(lock=False)
            #                   or not move.date
            #               ):
            #                   continue
            #
            # in felul acesta, move.name ramane '/' (setat la finalul metodei _compute_name)

            move_has_name = self.name and self.name != "/"
            if not move_has_name and self.state != "posted":
                return True

        return super()._get_last_sequence(relaxed=relaxed, lock=lock)

    def _set_next_sequence(self):
        self.ensure_one()
        cash_sequence = self.get_l10n_ro_sequence()
        if cash_sequence:
            last_sequence = (
                self._get_last_sequence(relaxed=True) or self._get_starting_sequence()
            )
            format_seq, format_values = self._get_sequence_format_param(last_sequence)
            if format_values["seq"] != 0:
                new_number = cash_sequence.next_by_id()
            else:
                # aici sunt in cazul in care s-a dat create(),
                # insa nu exista nimic in baza de date

                # nu incrementez deoarece daca se da discard, nu vreau sa
                # se incrementeze secventa
                new_number = False

            if new_number:
                self[self._sequence_field] = new_number

                self._compute_split_sequence()
        else:
            return super(AccountMove, self)._set_next_sequence()

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
                                # in care nu a existat nici o factura/nota in baza de date
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

        return super(AccountMove, self).write(vals)

    def _post(self, soft=True):
        for move in self:
            if move.is_l10n_ro_record:
                if move.payment_id and move.payment_id.state != "posted":
                    move.payment_id.l10n_ro_force_cash_sequence()
        return super()._post(soft)
