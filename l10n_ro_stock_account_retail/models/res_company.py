# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models

from odoo.addons.account.models.product import ACCOUNT_DOMAIN


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ro_account_markup_id = fields.Many2one(
        "account.account",
        string="Default Retail Markup Account (378)",
        check_company=True,
        domain=ACCOUNT_DOMAIN,
        help="Default markup account (adaos comercial) used as a fallback "
        "when no override is set on the location, product, or category.",
    )
    l10n_ro_account_deferred_vat_id = fields.Many2one(
        "account.account",
        string="Default Retail Deferred VAT Account (4428)",
        check_company=True,
        domain=ACCOUNT_DOMAIN,
        help="Default deferred VAT account (TVA neexigibila) used as a "
        "fallback when no override is set on the location, product, or "
        "category.",
    )
