# Copyright (C) 2026 NextERP Romania
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
        help="Markup account (adaos comercial) for this product. "
        "If empty, falls back to category, then to company default.",
    )
    l10n_ro_account_deferred_vat_id = fields.Many2one(
        "account.account",
        company_dependent=True,
        string="Deferred VAT Account (4428)",
        domain=ACCOUNT_DOMAIN,
        help="Deferred VAT account (TVA neexigibila) for this product. "
        "If empty, falls back to category, then to company default.",
    )

    def _l10n_ro_get_retail_price(self, warehouse=None, company=None):
        """Return the retail price (PVA) for the product in the warehouse.

        The price is the one configured on the warehouse retail pricelist;
        if no pricelist or no rule matches, falls back to ``list_price``.
        The price is returned in the company currency, the way it was
        configured on the pricelist (with or without VAT).
        """
        self.ensure_one()
        company = company or (warehouse.company_id if warehouse else self.env.company)
        pricelist = warehouse.l10n_ro_retail_pricelist_id if warehouse else False
        if pricelist:
            product = self.product_variant_id
            price = pricelist._get_product_price(product, 1.0)
            if pricelist.currency_id != company.currency_id:
                price = pricelist.currency_id._convert(
                    price,
                    company.currency_id,
                    company,
                    self.env.context.get("date") or pricelist.create_date,
                )
            return price
        return self.list_price or 0.0

    def _l10n_ro_get_retail_prices(self, warehouse=None, company=None):
        """Return a dict with the retail price split for the product.

        - ``price_without_vat``: retail price excluding VAT (base for 378)
        - ``price_with_vat``: retail price including VAT (matches 371)
        - ``vat``: deferred VAT amount (base for 4428)

        The base price is taken from the warehouse retail pricelist
        (falling back to ``list_price``). It is then interpreted through
        the company-specific sale taxes (``taxes_id``): if the tax is
        configured as price-included, the base is taken as PVA with VAT;
        otherwise the VAT is added on top.
        """
        self.ensure_one()
        company = company or (warehouse.company_id if warehouse else self.env.company)
        currency = company.currency_id
        base_price = self._l10n_ro_get_retail_price(
            warehouse=warehouse, company=company
        )
        taxes = self.taxes_id.filtered(lambda t: t.company_id == company)
        if not taxes:
            return {
                "price_without_vat": base_price,
                "price_with_vat": base_price,
                "vat": 0.0,
            }
        tax_res = taxes.compute_all(
            base_price, currency=currency, quantity=1.0, product=self
        )
        price_without_vat = tax_res["total_excluded"]
        price_with_vat = tax_res["total_included"]
        return {
            "price_without_vat": price_without_vat,
            "price_with_vat": price_with_vat,
            "vat": price_with_vat - price_without_vat,
        }
