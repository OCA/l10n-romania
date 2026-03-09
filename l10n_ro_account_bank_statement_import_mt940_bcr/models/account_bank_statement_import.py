# Copyright (C) 2022 Terrabit
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    def _is_bcr(self):
        if self._context.get("journal_id"):
            journal = self.env["account.journal"].browse(self._context["journal_id"])
            return journal.bank_account_id.bank_bic == "RNCBROBU"
        return self._context.get("mt940_ro_bcr")

    def _parse_file(self, data_file):
        if self._is_bcr():
            parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
            parser = parser.with_context(type="mt940_ro_bcr")
            data = parser.parse(data_file)
            if data:
                return self._post_parse_file(data)
        return super()._parse_file(data_file)

    def _post_parse_file(self, data):
        currency, account_num, all_statements = data
        for statements in all_statements:
            for transaction in statements["transactions"]:
                vat = transaction.pop("vat", False)
                if vat:
                    domain = [("vat", "like", vat), ("is_company", "=", True)]
                    partner = self.env["res.partner"].search(domain, limit=1)
                    if partner:
                        transaction["partner_name"] = partner.name
                        transaction["partner_id"] = partner.id
        return data
