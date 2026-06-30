# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    def _is_bt(self):
        if self._context.get("journal_id"):
            journal = self.env["account.journal"].browse(self._context["journal_id"])
            return journal.bank_account_id.bank_bic == "BTRLRO22"
        return self._context.get("mt940_ro_bt")

    def _parse_file(self, data_file):
        if self._is_bt():
            parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
            parser = parser.with_context(type="mt940_ro_bt")
            data = parser.parse(data_file)
            if data:
                currency, account_number, statements = data
                for stmt in statements:
                    stmt.pop("_bt_closed", None)
                bank = self.env.company.bank_ids.filtered(
                    lambda b: account_number in b.sanitized_acc_number
                )
                if bank:
                    return (currency, bank.sanitized_acc_number, statements)
                return (currency, account_number, statements)
        return super()._parse_file(data_file)
