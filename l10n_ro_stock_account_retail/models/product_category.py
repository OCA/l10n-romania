# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models

from odoo.addons.account.models.product import ACCOUNT_DOMAIN


class ProductCategory(models.Model):
    _inherit = "product.category"

    l10n_ro_account_markup_id = fields.Many2one(
        "account.account",
        company_dependent=True,
        string="Markup Account (378)",
        domain=ACCOUNT_DOMAIN,
        help="Markup account (adaos comercial) used for retail accounting. "
        "Falls back to the company default if empty.",
    )
    l10n_ro_account_deferred_vat_id = fields.Many2one(
        "account.account",
        company_dependent=True,
        string="Deferred VAT Account (4428)",
        domain=ACCOUNT_DOMAIN,
        help="Deferred VAT account (TVA neexigibila) used for retail "
        "accounting. Falls back to the company default if empty.",
    )
