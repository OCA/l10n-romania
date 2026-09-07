# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _l10n_ro_get_retail_price(self, warehouse=None, company=None):
        """Return the shelf price (PVA) of this variant, VAT included.

        The price comes from the warehouse retail pricelist; with no pricelist
        or no matching rule it falls back to the variant sale price.

        The retail price is held **VAT included** everywhere in this family of
        modules: that is the figure on the shelf label, the figure the customer
        pays, and the figure that has to match account 371. Reading it as a net
        price and adding VAT on top - which is what this method used to do -
        contradicted the price change document, which has always split a
        VAT-inclusive PVA, and produced two different retail prices for the same
        product depending on which code path asked.

        The price is resolved per variant. Asking the template for it made every
        variant of a template share the price of its first variant, so a shop
        with sizes or colours priced differently posted the wrong markup on all
        but one of them.
        """
        self.ensure_one()
        company = company or (warehouse.company_id if warehouse else self.env.company)
        pricelist = warehouse.l10n_ro_retail_pricelist_id if warehouse else False
        if not pricelist:
            return self.with_company(company).lst_price or 0.0
        price = pricelist._get_product_price(self, 1.0)
        if pricelist.currency_id and pricelist.currency_id != company.currency_id:
            price = pricelist.currency_id._convert(
                price,
                company.currency_id,
                company,
                self.env.context.get("date") or fields.Date.context_today(self),
            )
        return price

    def _l10n_ro_get_retail_prices(self, warehouse=None, company=None):
        """Return the shelf price of this variant split in three:

        - ``price_with_vat``: the PVA itself, what account 371 must carry
        - ``price_without_vat``: the base the markup (378) is measured against
        - ``vat``: the deferred VAT (4428) included in the PVA
        """
        self.ensure_one()
        company = company or (warehouse.company_id if warehouse else self.env.company)
        price_with_vat = self._l10n_ro_get_retail_price(
            warehouse=warehouse, company=company
        )
        return self._l10n_ro_split_retail_price(price_with_vat, company=company)

    def _l10n_ro_split_retail_price(self, price_with_vat, company=None):
        """Split a VAT-inclusive retail price using the variant sale taxes."""
        self.ensure_one()
        company = company or self.env.company
        empty = {
            "price_without_vat": price_with_vat,
            "price_with_vat": price_with_vat,
            "vat": 0.0,
        }
        if not price_with_vat:
            return empty
        taxes = self.taxes_id.filtered(lambda t: t.company_id == company)
        if not taxes:
            return empty
        tax_res = taxes.with_context(force_price_include=True).compute_all(
            price_with_vat,
            currency=company.currency_id,
            quantity=1.0,
            product=self,
        )
        price_without_vat = tax_res["total_excluded"]
        return {
            "price_without_vat": price_without_vat,
            "price_with_vat": price_with_vat,
            "vat": price_with_vat - price_without_vat,
        }

    def _l10n_ro_minimum_retail_price(self, cost_unit, company=None):
        """Lowest PVA that keeps the markup non negative, VAT included.

        Used to tell the user what to fix when a shelf price would book a
        negative markup, instead of only telling them that it does.
        """
        self.ensure_one()
        company = company or self.env.company
        taxes = self.taxes_id.filtered(lambda t: t.company_id == company)
        if not taxes:
            return cost_unit
        tax_res = taxes.with_context(force_price_include=False).compute_all(
            cost_unit, currency=company.currency_id, quantity=1.0, product=self
        )
        return tax_res["total_included"]
