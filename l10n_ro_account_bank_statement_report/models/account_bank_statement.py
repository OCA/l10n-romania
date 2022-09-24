# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountBankStatement(models.Model):
    _name = "account.bank.statement"
    _inherit = ["account.bank.statement", "l10n.ro.mixin"]
