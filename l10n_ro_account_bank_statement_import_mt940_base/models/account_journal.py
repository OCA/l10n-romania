# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_bank_statements_available_import_formats(self):
        res = super(
            AccountJournal, self
        )._get_bank_statements_available_import_formats()
        res.extend([("mt940_general")])
        return res

    def _statement_line_import_speeddict(self):
        """This method is designed to be inherited by reconciliation modules.
        These modules can take advantage of this method to pre-fetch data
        that will later be used for many statement lines (to avoid
        searching data for each statement line).
        The goal is to improve performances.
        """
        speeddict = super()._statement_line_import_speeddict()
        partner_banks = self.env["res.partner.bank"].search_read(
            [("company_id", "in", (False, self.company_id.id))],
            ["sanitized_acc_number", "partner_id"],
        )
        for partner_bank in partner_banks:
            speeddict["account_number"][partner_bank["sanitized_acc_number"]] = {
                "partner_id": partner_bank["partner_id"][0],
                "partner_bank_id": partner_bank["id"],
            }
        return speeddict
