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

    def _l10n_ro_resolve_account(
        self, field_name, product=None, categ_field=None, on_company=False
    ):
        """Resolve a retail account: location (walking up its parents) ->
        product -> category -> company, then the fiscal position of the shop.

        The walk up the parent chain is what makes the setting usable: a shop
        is configured once on the warehouse stock location, and the shelf, bin
        and counter sublocations created under it inherit the accounts. Read
        strictly on the location itself, a putaway rule that moves goods one
        level down silently fell through to the company default.

        The fiscal position is the same ``l10n_ro_fiscal_position_id`` the
        Romanian stock accounting already applies to the valuation accounts of
        a warehouse. A shop that keeps its goods on 371.1 rather than 371 maps
        them once there instead of overriding every product, every category
        and every location - and the markup and the deferred VAT go through
        the same map, so the three accounts an entry touches stay in the same
        set of books. It is applied per leg, on the location's own warehouse,
        so a transfer between two shops resolves each side against its own.

        The three accounts differ only in where they are named: 371 carries
        another name on the category and has no company default, the markup
        and the deferred VAT are called the same thing all the way up.
        """
        self.ensure_one()
        company = self.company_id or self.env.company
        location = self.with_company(company)
        account = self.env["account.account"]
        while location and not account:
            account = location[field_name]
            location = location.location_id
        if not account and product:
            product = product.with_company(company)
            account = product[field_name] or product.categ_id[categ_field or field_name]
        if not account and on_company:
            account = company[field_name]
        fiscal_position = self.warehouse_id.l10n_ro_fiscal_position_id
        if account and fiscal_position:
            account = fiscal_position.map_account(account)
        return account

    def _l10n_ro_get_markup_account(self, product=None):
        return self._l10n_ro_resolve_account(
            "l10n_ro_account_markup_id", product=product, on_company=True
        )

    def _l10n_ro_get_deferred_vat_account(self, product=None):
        return self._l10n_ro_resolve_account(
            "l10n_ro_account_deferred_vat_id", product=product, on_company=True
        )

    def _l10n_ro_get_stock_account(self, product=None):
        """The stock valuation account (371) the retail entries hit."""
        return self._l10n_ro_resolve_account(
            "l10n_ro_property_stock_valuation_account_id",
            product=product,
            categ_field="property_stock_valuation_account_id",
        )
