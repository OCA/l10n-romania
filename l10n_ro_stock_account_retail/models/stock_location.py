# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models

from odoo.addons.account.models.product import ACCOUNT_DOMAIN


class StockLocation(models.Model):
    _inherit = "stock.location"

    l10n_ro_retail = fields.Boolean(
        string="Retail Location",
        compute="_compute_l10n_ro_retail",
        store=True,
        help="Internal location belonging to a retail warehouse. "
        "Stock movements in/out generate the 378/4428 markup entries.",
    )
    l10n_ro_account_markup_id = fields.Many2one(
        "account.account",
        string="Markup Account (378)",
        company_dependent=True,
        domain=ACCOUNT_DOMAIN,
        help="Account used for the commercial markup (adaos comercial) "
        "between cost and retail price without VAT. Overrides the product / "
        "category / company defaults.",
    )
    l10n_ro_account_deferred_vat_id = fields.Many2one(
        "account.account",
        string="Deferred VAT Account (4428)",
        company_dependent=True,
        domain=ACCOUNT_DOMAIN,
        help="Account used for the VAT included in the retail price but "
        "not yet collected (TVA neexigibila). Overrides the product / "
        "category / company defaults.",
    )

    @api.depends("usage", "warehouse_id", "warehouse_id.l10n_ro_retail")
    def _compute_l10n_ro_retail(self):
        for location in self:
            location.l10n_ro_retail = bool(
                location.usage == "internal"
                and location.warehouse_id
                and location.warehouse_id.l10n_ro_retail
            )

    def _l10n_ro_resolve_account(self, field_name, product=None):
        """Resolve the retail account in order: location -> product -> category
        -> company.
        """
        self.ensure_one()
        account = self[field_name]
        if account:
            return account
        if product:
            product = product.with_company(self.company_id)
            tmpl_account = product.product_tmpl_id[field_name]
            if tmpl_account:
                return tmpl_account
            cat_account = product.categ_id[field_name]
            if cat_account:
                return cat_account
        return self.company_id[field_name]

    def _l10n_ro_get_markup_account(self, product=None):
        return self._l10n_ro_resolve_account(
            "l10n_ro_account_markup_id", product=product
        )

    def _l10n_ro_get_deferred_vat_account(self, product=None):
        return self._l10n_ro_resolve_account(
            "l10n_ro_account_deferred_vat_id", product=product
        )
