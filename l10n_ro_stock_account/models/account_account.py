# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountAccount(models.Model):
    _name = "account.account"
    _inherit = ["account.account", "l10n.ro.mixin"]

    l10n_ro_stock_consume_account_id = fields.Many2one(
        "account.account",
        string="Romania - Consume Account",
        company_dependent=True,
        domain="[('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        help="Account used for stock consume and usage giving operations",
    )
