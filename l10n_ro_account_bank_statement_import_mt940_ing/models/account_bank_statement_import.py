# Copyright (C) 2016 Forest and Biomass Romania
# Copyright (C) 2022 Terrabit
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    def _parse_file(self, data_file):
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_ing")
        data = parser.parse(data_file)
        if data:
            account_number = data[1].split("/")[1]
            bank = self.env.company.bank_ids.filtered(
                lambda b: account_number in b.sanitized_acc_number
            )
            if bank:
                return (data[0], bank.sanitized_acc_number, data[2])
            return data
        return super(AccountBankStatementImport, self)._parse_file(data_file)
