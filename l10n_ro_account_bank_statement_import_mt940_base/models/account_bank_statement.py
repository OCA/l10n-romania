# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _find_or_create_bank_account(self):
        self.ensure_one()
        if (
            self.company_id.country_id.code == "RO"
            and self.partner_id.id == self.company_id.partner_id.id
        ):
            return self.env["res.partner.bank"]
        else:
            return super()._find_or_create_bank_account()
