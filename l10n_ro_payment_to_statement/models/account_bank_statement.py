# Copyright (C) 2015-2020 Deltatech
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import api, fields, models


class AccountBankStatement(models.Model):
    _name = "account.bank.statement"
    _inherit = ["account.bank.statement", "l10n.ro.mixin"]

    @api.model
    def _l10n_ro_get_journal(self, vals):
        """Journal a statement is being created for.

        It is not always given: a statement made out of its lines takes the
        journal from them.
        """
        journal = self.env["account.journal"].browse(vals.get("journal_id"))
        if not journal and vals.get("line_ids"):
            journal = self.new(vals).journal_id
        return journal

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name") not in [None, "/", "", False]:
                continue
            # the company of a statement is the one of its journal, which is
            # not necessarily the company the user is working in
            journal = self._l10n_ro_get_journal(vals)
            if not journal.company_id._check_is_l10n_ro_record():
                continue
            if journal.l10n_ro_statement_sequence_id:
                vals["name"] = journal.l10n_ro_statement_sequence_id.next_by_id()
            else:
                # sper sa nu fie doua statementuri in aceeasi zi
                vals["name"] = fields.Date.to_string(fields.Date.today())
        return super().create(vals_list)

    def _compute_display_name(self):
        res = super()._compute_display_name()
        for record in self:
            if record.is_l10n_ro_record and record.name == "/":
                record.display_name = fields.Date.to_string(record.date)
        return res

    @api.model
    def _l10n_ro_get_statement(self, journal, date):
        """Cash register of a journal for a given day, created when missing."""
        statement = self.search(
            [("journal_id", "=", journal.id), ("date", "=", date)], limit=1
        )
        if not statement:
            statement = self.sudo().create({"journal_id": journal.id, "date": date})
        return statement


class AccountBankStatementLine(models.Model):
    _name = "account.bank.statement.line"
    _inherit = ["account.bank.statement.line", "l10n.ro.mixin"]

    is_l10n_ro_payment_disposal = fields.Boolean()

    def _l10n_ro_move_to_statement_of_the_day(self):
        """Keep the line in the register of the day it is dated.

        A payment can be cancelled, dated another day and posted again. A
        register takes the date of its lines, so one holding a single line
        simply follows it; one holding lines of another day would end up
        spanning two days, and the line moves out of it.
        """
        for line in self:
            statement = line.statement_id
            if statement and all(
                other.date == line.date for other in statement.line_ids
            ):
                continue
            # leave first, so that the register takes its own date back
            line.statement_id = False
            line.statement_id = self.env[
                "account.bank.statement"
            ]._l10n_ro_get_statement(line.journal_id, line.date)

    def _l10n_ro_stands_for(self, payment):
        """The line still says what the payment says."""
        self.ensure_one()
        amount = (
            -payment.amount if payment.payment_type == "outbound" else payment.amount
        )
        return (
            self.date == payment.date
            and self.currency_id.compare_amounts(self.amount, amount) == 0
            and self.partner_id == payment.partner_id
        )

    def _l10n_ro_drop(self):
        """Take the line out of the register, with what it reconciled."""
        for line in self:
            line.move_id.line_ids.remove_move_reconcile()
            # a valid and complete register does not let its lines go,
            # see account.bank.statement.line._check_allow_unlink
            line.statement_id = False
            line.unlink()

    def _l10n_ro_get_payment(self):
        """Payment this cash register line stands for, if any."""
        self.ensure_one()
        return self.env["account.payment"].search(
            [("l10n_ro_statement_line_id", "=", self.id)], limit=1
        )

    def _synchronize_to_moves(self, changed_fields):
        # A line standing for a payment is written by the payment itself. The
        # standard synchronization rebuilds the entry as liquidity + suspense
        # and drops every other line, which would remove the receivable/payable
        # line of the payment, or its outstanding line, undoing the
        # reconciliation with the invoice.
        lines = self.filtered(
            lambda line: not (
                line.is_l10n_ro_record
                and line.journal_id.type == "cash"
                and line._l10n_ro_get_payment()
            )
        )
        return super(AccountBankStatementLine, lines)._synchronize_to_moves(
            changed_fields
        )
