# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
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
        help="Account used for the commercial markup "
        "between cost and retail price without VAT. Applies to this location "
        "and, unless they override it, to its sublocations. Overrides the "
        "product / category / company defaults.",
    )
    l10n_ro_account_deferred_vat_id = fields.Many2one(
        "account.account",
        string="Deferred VAT Account (4428)",
        company_dependent=True,
        domain=ACCOUNT_DOMAIN,
        help="Account used for the VAT included in the retail price but "
        "not yet collected. Applies to this location and, "
        "unless they override it, to its sublocations. Overrides the "
        "product / category / company defaults.",
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
        """Resolve a retail account: location (walking up its parents) ->
        product -> category -> company.

        The walk up the parent chain is what makes the setting usable: a shop
        is configured once on the warehouse stock location, and the shelf, bin
        and counter sublocations created under it inherit both accounts. Read
        strictly on the location itself, a putaway rule that moves goods one
        level down silently fell through to the company default.
        """
        self.ensure_one()
        company = self.company_id or self.env.company
        location = self.with_company(company)
        while location:
            account = location[field_name]
            if account:
                return account
            location = location.location_id
        if product:
            product = product.with_company(company)
            tmpl_account = product.product_tmpl_id[field_name]
            if tmpl_account:
                return tmpl_account
            cat_account = product.categ_id[field_name]
            if cat_account:
                return cat_account
        return company[field_name]

    def _l10n_ro_get_markup_account(self, product=None):
        return self._l10n_ro_resolve_account(
            "l10n_ro_account_markup_id", product=product
        )

    def _l10n_ro_get_deferred_vat_account(self, product=None):
        return self._l10n_ro_resolve_account(
            "l10n_ro_account_deferred_vat_id", product=product
        )

    def _l10n_ro_get_stock_account(self, product=None):
        """Resolve the stock valuation account (371) the retail entries hit.

        Same order as the core Romanian stock accounting: location override
        first - walked up the parents, like the markup accounts - then the
        product, then its category.
        """
        self.ensure_one()
        company = self.company_id or self.env.company
        location = self.with_company(company)
        while location:
            account = location.l10n_ro_property_stock_valuation_account_id
            if account:
                return account
            location = location.location_id
        if product:
            product = product.with_company(company)
            return (
                product.l10n_ro_property_stock_valuation_account_id
                or product.categ_id.property_stock_valuation_account_id
            )
        return self.env["account.account"]
