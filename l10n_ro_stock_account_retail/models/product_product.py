# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _l10n_ro_get_retail_price(self, warehouse=None, company=None):
        """Return the shelf price (PVA) of this variant, VAT included.

        The price comes from a rule on the warehouse retail pricelist, and only
        from there. A product moving in or out of a shop without one is an
        incomplete configuration, and it is refused instead of guessed.

        There used to be a fallback on the variant sale price. It was silent
        and it was wrong: ``lst_price`` is a **net** price in any standard
        Romanian setup - the taxes of the Romanian chart are not price
        included - while the retail price is held **VAT included** everywhere
        in this family of modules. That is the figure on the shelf label, the
        figure the customer pays, and the figure that has to match account 371.
        Reading a net price as a VAT inclusive one books the net price on 371,
        understates the markup on 378 and computes 4428 on a different base.

        Refusing only when the warehouse has no pricelist at all would not
        close the gap either: ``_compute_price_rule`` answers with the product
        sale price whenever no rule matches, so a shop with a pricelist and one
        unpriced product lands in exactly the same place. The check is
        therefore on the rule, per product.

        The price is resolved per variant. Asking the template for it made every
        variant of a template share the price of its first variant, so a shop
        with sizes or colours priced differently posted the wrong markup on all
        but one of them.
        """
        self.ensure_one()
        company = company or (warehouse.company_id if warehouse else self.env.company)
        pricelist = warehouse.l10n_ro_retail_pricelist_id if warehouse else False
        price, rule_id = (0.0, False)
        if pricelist:
            price, rule_id = pricelist._get_product_price_rule(self, 1.0)
        if not rule_id:
            raise UserError(
                self.env._(
                    "No shelf price (PVA) for %(product)s in %(warehouse)s.\n\n"
                    "The retail price has to come from a rule on the retail "
                    "pricelist of the warehouse, VAT included: it is what "
                    "account 371 carries, and the markup on 378 is measured "
                    "against it. Add a price for this product on the retail "
                    "pricelist %(pricelist)s.",
                    product=self.display_name,
                    warehouse=warehouse.display_name
                    if warehouse
                    else self.env._("this warehouse"),
                    pricelist=pricelist.display_name
                    if pricelist
                    else self.env._("(none set on the warehouse)"),
                )
            )
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
        return self._l10n_ro_split_retail_price(
            price_with_vat, company=company, warehouse=warehouse
        )

    def _l10n_ro_retail_taxes(self, warehouse=None, company=None):
        """The taxes the shelf price of this variant is split with.

        The sale taxes of the product, mapped through the fiscal position of
        the shop - the same ``l10n_ro_fiscal_position_id`` the Romanian stock
        accounting already uses to map the valuation accounts of a warehouse.

        Reading ``taxes_id`` raw is not the same thing. A company that sells
        both retail and B2B keeps one set of taxes on the product and maps
        them per shop: to the VAT included variants a till works with, or to
        another rate altogether. The VAT loaded on 4428 has to be the one the
        shop will actually collect, so it is the mapped taxes that split the
        price, not the ones the product happens to carry for everybody else.
        """
        self.ensure_one()
        company = company or (warehouse.company_id if warehouse else self.env.company)
        taxes = self.taxes_id.filtered(lambda t: t.company_id == company)
        fiscal_position = warehouse.l10n_ro_fiscal_position_id if warehouse else False
        if fiscal_position:
            taxes = fiscal_position.map_tax(taxes)
        return taxes

    def _l10n_ro_retail_vat_taxes(self, warehouse=None, company=None):
        """The VAT among the shop's taxes for this variant."""
        self.ensure_one()
        taxes = self._l10n_ro_retail_taxes(warehouse=warehouse, company=company)
        return taxes.filtered(lambda t: t._l10n_ro_is_retail_vat())

    def _l10n_ro_split_retail_price(self, price_with_vat, company=None, warehouse=None):
        """Split a VAT-inclusive retail price using the shop's sale taxes.

        The price is read as VAT inclusive whatever the taxes say about
        themselves - ``force_price_include`` - because a shelf price is a PVA
        by definition. So a fiscal position that maps the product's ordinary
        taxes to their price included variants changes nothing here, which is
        the point: what the mapping is there to change is the rate, and that
        the split does follow.

        Only the VAT part goes to 4428. Anything else the shop charges on top
        - a packaging deposit, an eco fee, marked with *Not VAT (Retail)* on
        the tax - is collected for somebody else: it is neither markup nor
        deferred VAT, so it is taken out of the retail value altogether
        instead of being posted to 4428 as VAT that was never owed, or left in
        the base and posted to 378 as markup the shop never made.
        """
        self.ensure_one()
        company = company or (warehouse.company_id if warehouse else self.env.company)
        empty = {
            "price_without_vat": price_with_vat,
            "price_with_vat": price_with_vat,
            "vat": 0.0,
        }
        if not price_with_vat:
            return empty
        taxes = self._l10n_ro_retail_taxes(warehouse=warehouse, company=company)
        if not taxes:
            return empty
        tax_res = taxes.with_context(force_price_include=True).compute_all(
            price_with_vat,
            currency=company.currency_id,
            quantity=1.0,
            product=self,
        )
        # A group tax expands to its children, so the taxes that come back are
        # not necessarily the ones that went in.
        computed = self.env["account.tax"].browse(
            [line["id"] for line in tax_res["taxes"]]
        )
        vat_ids = set(computed.filtered(lambda t: t._l10n_ro_is_retail_vat()).ids)
        vat = sum(line["amount"] for line in tax_res["taxes"] if line["id"] in vat_ids)
        other = sum(
            line["amount"] for line in tax_res["taxes"] if line["id"] not in vat_ids
        )
        return {
            "price_without_vat": tax_res["total_excluded"],
            "price_with_vat": price_with_vat - other,
            "vat": vat,
        }

    def _l10n_ro_minimum_retail_price(self, cost_unit, company=None, warehouse=None):
        """Lowest PVA that keeps the markup non negative, VAT included.

        Used to tell the user what to fix when a shelf price would book a
        negative markup, instead of only telling them that it does.
        """
        self.ensure_one()
        company = company or (warehouse.company_id if warehouse else self.env.company)
        taxes = self._l10n_ro_retail_vat_taxes(warehouse=warehouse, company=company)
        if not taxes:
            return cost_unit
        tax_res = taxes.with_context(force_price_include=False).compute_all(
            cost_unit, currency=company.currency_id, quantity=1.0, product=self
        )
        return tax_res["total_included"]
