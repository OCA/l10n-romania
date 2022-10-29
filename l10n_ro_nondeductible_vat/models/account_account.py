# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountTaxExtend(models.Model):
    _name = "account.account"
    _inherit = ["account.account", "l10n.ro.mixin"]

    l10n_ro_nondeductible_account_id = fields.Many2one(
        "account.account", string="Romania - Nondeductible Account"
    )
