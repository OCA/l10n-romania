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
    #

    def _get_journal_dashboard_data_batched(self):
        datas = super()._get_journal_dashboard_data_batched()

        for journal in self.filtered("is_l10n_ro_record"):
            currency = journal.currency_id or journal.company_id.currency_id

            amount_field = (
                "balance"
                if (
                    not journal.currency_id
                    or journal.currency_id == journal.company_id.currency_id
                )
                else "amount_currency"
            )
            account_transfer_sum = 0.0
            if journal.company_id.transfer_account_id and journal.type not in [
                "cash",
                "bank",
            ]:
                query = """
                SELECT sum(balance) as balance, sum(amount_currency)  as amount_currency
                FROM account_move_line
                WHERE
                 parent_state = 'posted' AND account_id = %s AND date <= %s;
                """
                self.env.cr.execute(
                    query,
                    (journal.company_id.transfer_account_id.id, fields.Date.today()),
                )
                query_results = self.env.cr.dictfetchall()
                if query_results and query_results[0].get(amount_field) is not None:
                    account_transfer_sum = query_results[0].get(amount_field)

            datas[journal.id]["account_transfer_balance"] = formatLang(
                self.env,
                currency.round(account_transfer_sum) + 0.0,
                currency_obj=currency,
            )
        return datas

    @api.model
    def _fill_missing_values(self, vals, protected_codes=False):
        res = super()._fill_missing_values(vals, protected_codes)
        if not vals:
            vals = {}
        if (
            self.env["res.company"]._check_is_l10n_ro_record(
                company=vals.get("company_id")
            )
            and vals.get("type", "") == "cash"
        ):
            l10n_ro_sequence_fields = {
                "l10n_ro_journal_sequence_id": "",
                "l10n_ro_statement_sequence_id": "RC",
                "l10n_ro_cash_in_sequence_id": "DI",
                "l10n_ro_cash_out_sequence_id": "DP",
                "l10n_ro_customer_cash_in_sequence_id": "CH",
            }
            journal_code = vals.get("code") or self.env[
                "account.journal"
            ].get_next_bank_cash_default_code("cash", self.env.company)
            journal_name = vals.get("name") or ""
            company = vals.get("company_id") or self.env.company.id
            vals[
                "sequence_override_regex"
            ] = r"^(?P<prefix1>.*?)(?P<seq>\d*)(?P<suffix>\D*?)$"
            for seq_field, code in l10n_ro_sequence_fields.items():
                if not vals.get(seq_field):
                    vals_seq = {
                        "name": f"{journal_name} - {seq_field}",
                        "code": f"{journal_code}{code}",
                        "implementation": "no_gap",
                        "prefix": f"{journal_code}{code}",
                        "suffix": "",
                        "padding": 6,
                        "company_id": company,
                    }
                    seq = self.env["ir.sequence"].sudo().create(vals_seq)
                    vals[seq_field] = seq.id
        return res

    def l10n_ro_update_cash_vals(self):
        self.ensure_one()
        customer_cash_in_sequence_id = self.l10n_ro_customer_cash_in_sequence_id.id
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
            "l10n_ro_customer_cash_in_sequence_id": customer_cash_in_sequence_id,
        }
        self._fill_missing_values(new_vals)
        # cannot write type when journal is used in POS
        new_vals.pop("type")
        self.write(new_vals)
