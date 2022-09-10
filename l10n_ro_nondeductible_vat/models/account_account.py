# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountTaxExtend(models.Model):
    _inherit = "account.account"

    nondeductible_account_id = fields.Many2one("account.account")
