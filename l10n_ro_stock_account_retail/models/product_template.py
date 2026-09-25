# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models

from odoo.addons.account.models.product import ACCOUNT_DOMAIN


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_ro_account_markup_id = fields.Many2one(
        "account.account",
        company_dependent=True,
        string="Markup Account (378)",
        domain=ACCOUNT_DOMAIN,
        help="Markup account for this product. "
        "If empty, falls back to category, then to company default.",
    )
    l10n_ro_account_deferred_vat_id = fields.Many2one(
        "account.account",
        company_dependent=True,
        string="Deferred VAT Account (4428)",
        domain=ACCOUNT_DOMAIN,
        help="Deferred VAT account for this product. "
        "If empty, falls back to category, then to company default.",
    )
