# Copyright (C) 2015-2020 Deltatech
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import fields, models
from odoo.tools.misc import formatLang


class AccountJournal(models.Model):
    _name = "account.journal"
    _inherit = ["account.journal", "l10n.ro.mixin"]

    l10n_ro_statement_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Romania - Statement Sequence",
        copy=False,
        help="Sequence used for statement name",
    )
    l10n_ro_auto_statement = fields.Boolean(
        string="Romania - Auto Statement",
        help="Automatically add payments with this journal to a statement",
    )
    l10n_ro_journal_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Romania - Sequence Journal",
        copy=False,
        help="Sequence used for other (closing, line) account move names",
    )
    l10n_ro_cash_in_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Romania - Sequence cash in",
        copy=False,
        help="Sequence used for cash in operations",
    )
    l10n_ro_cash_out_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Romania - Sequence cash out",
        copy=False,
        help="Sequence used for cash out operations",
    )
    l10n_ro_customer_cash_in_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Romania - Customer sequence cash in",
        copy=False,
        help="Sequence used for customer cash in operations (customer payments)",
    )

    def get_journal_dashboard_datas(self):
        if self.is_l10n_ro_record:
            currency = self.currency_id or self.company_id.currency_id
            amount_field = (
                "balance"
                if (
                    not self.currency_id
                    or self.currency_id == self.company_id.currency_id
                )
                else "amount_currency"
            )
            account_transfer_sum = 0.0
            if self.company_id.transfer_account_id:
                query = """
                SELECT sum(balance) as balance, sum(amount_currency)  as amount_currency
                FROM account_move_line
                WHERE
                 parent_state = 'posted' AND account_id = %s AND date <= %s;
                """
                self.env.cr.execute(
                    query, (self.company_id.transfer_account_id.id, fields.Date.today())
                )
                query_results = self.env.cr.dictfetchall()
                if query_results and query_results[0].get(amount_field) is not None:
                    account_transfer_sum = query_results[0].get(amount_field)

        datas = super(AccountJournal, self).get_journal_dashboard_datas()
        if self.is_l10n_ro_record:
            datas["account_transfer_balance"] = formatLang(
                self.env,
                currency.round(account_transfer_sum) + 0.0,
                currency_obj=currency,
            )
        return datas
