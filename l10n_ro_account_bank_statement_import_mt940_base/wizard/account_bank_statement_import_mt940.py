from odoo import models


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    def _parse_file(self, data_file):
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_general")
        data = parser.parse(data_file)
        if data:
            return data
        return super(AccountBankStatementImport, self)._parse_file(data_file)
