# Copyright (C) 2015-2020 Deltatech
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import api, fields, models
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

    @api.model
    def _fill_missing_values(self, vals):
        super()._fill_missing_values(vals)
        if not vals:
            vals = {}
        if (
            self.env["res.company"]._check_is_l10n_ro_record(
                company=vals.get("company_id")
            )
            and vals.get("type", "") == "cash"
        ):
            l10n_ro_sequnce_fields = {
                "l10n_ro_journal_sequence_id": "",
                "l10n_ro_statement_sequence_id": "RC",
                "l10n_ro_cash_in_sequence_id": "DI",
                "l10n_ro_cash_out_sequence_id": "DP",
                "l10n_ro_customer_cash_in_sequence_id": "CH",
            }
            journal_code = vals.get("code") or ""
            journal_name = vals.get("name") or ""
            company = vals.get("company_id") or self.env.company.id
            for seq_field, code in l10n_ro_sequnce_fields.items():
                if not vals.get(seq_field):
                    vals_seq = {
                        "name": "%s - %s" % (journal_name, seq_field),
                        "code": "%s%s" % (journal_code, code),
                        "implementation": "no_gap",
                        "prefix": "%s%s-" % (journal_code, code),
                        "suffix": "",
                        "padding": 6,
                        "company_id": company,
                    }
                    seq = self.env["ir.sequence"].create(vals_seq)
                    vals[seq_field] = seq.id

    def l10n_ro_update_cash_vals(self):
        self.ensure_one()
        new_vals = {
            "type": self.type,
            "name": self.name,
            "code": self.code,
            "company_id": self.company_id.id,
            "l10n_ro_auto_statement": True,
            "l10n_ro_journal_sequence_id": self.l10n_ro_journal_sequence_id.id,
            "l10n_ro_statement_sequence_id": self.l10n_ro_statement_sequence_id.id,
            "l10n_ro_cash_in_sequence_id": self.l10n_ro_cash_in_sequence_id.id,
            "l10n_ro_cash_out_sequence_id": self.l10n_ro_cash_out_sequence_id.id,
        }
        new_vals[
            "l10n_ro_customer_cash_in_sequence_id"
        ] = self.l10n_ro_customer_cash_in_sequence_id.id
        self._fill_missing_values(new_vals)
        self.write(new_vals)
