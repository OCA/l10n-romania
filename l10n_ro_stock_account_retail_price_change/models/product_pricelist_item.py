# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models

TRIGGER_FIELDS = {
    # What the rule prices, and what it answers with.
    "fixed_price",
    "compute_price",
    "applied_on",
    "product_id",
    "product_tmpl_id",
    "categ_id",
    "pricelist_id",
    # A formula answers with a price just as much as a fixed rule does, and
    # every term of it moves the label: the base it starts from, the discount
    # or markup over that base, the rounding, the extra fee, the margins it is
    # held between. A shop that prices its shelves as a markup over the buying
    # list changes its prices here and nowhere else.
    "base",
    "base_pricelist_id",
    "price_discount",
    "price_markup",
    "price_round",
    "price_surcharge",
    "price_min_margin",
    "price_max_margin",
    # A promotion is a shelf price too. Editing its window can make it
    # effective, or stop it being effective, right now - and then the label
    # changes with it. What this cannot catch is the day a future window
    # opens on its own: nothing is written then, and the price a pricelist
    # answers with simply becomes another one. The nightly reconciliation on
    # the document itself is what catches that.
    "date_start",
    "date_end",
    # The rule for quantity 1 is the one on the label.
    "min_quantity",
}


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    # ------------------------------------------------------------------
    # Which shelves a rule can move
    # ------------------------------------------------------------------
    @api.model
    def _l10n_ro_retail_warehouses(self, pricelists):
        """Retail warehouses whose shelf prices depend on each of ``pricelists``.

        Directly, when a warehouse prices its shelves from one of them. And
        indirectly, when its retail pricelist is computed as a formula over
        one of them - the ordinary way a shop keeps its shelf prices at a
        markup over a buying list, or a group list. Following only the direct
        link meant the whole chain was invisible: the buyer moved a price on
        the list the shop derives from, every label in the shop moved with it,
        and nothing was raised because the rule that was written did not live
        on the shop's own pricelist.

        The chain is walked to a fixed point, so a list derived from a list
        derived from the edited one is found too, and a cycle terminates. The
        dependency graph is read once for the whole database - there are as
        many edges as there are rules based on another pricelist, which is a
        handful - and then walked per edited pricelist, because the answer has
        to say which warehouses *that* pricelist reaches.

        :returns: ``{edited_pricelist_id: [warehouse, ...]}``
        """
        if not pricelists:
            return {}
        edges = {}
        for pricelist, base in (
            self.env["product.pricelist.item"]
            .sudo()
            ._read_group(
                [("base", "=", "pricelist"), ("base_pricelist_id", "!=", False)],
                groupby=["pricelist_id", "base_pricelist_id"],
            )
        ):
            edges.setdefault(base.id, set()).add(pricelist.id)
        by_retail_pricelist = {}
        for warehouse in self.env["stock.warehouse"].search(
            [
                ("l10n_ro_retail", "=", True),
                ("l10n_ro_retail_pricelist_id", "!=", False),
            ]
        ):
            by_retail_pricelist.setdefault(
                warehouse.l10n_ro_retail_pricelist_id.id, []
            ).append(warehouse)
        if not by_retail_pricelist:
            return {}
        result = {}
        for pricelist in pricelists:
            reachable = {pricelist.id}
            frontier = {pricelist.id}
            while frontier:
                frontier = (
                    set().union(*(edges.get(pl_id, set()) for pl_id in frontier))
                    - reachable
                )
                reachable |= frontier
            warehouses = [
                warehouse
                for pl_id in reachable
                for warehouse in by_retail_pricelist.get(pl_id, [])
            ]
            if warehouses:
                result[pricelist.id] = warehouses
        return result

    def _l10n_ro_scope_products(self, products):
        """The subset of ``products`` this rule can price.

        Every kind of rule is followed, not only a fixed price set on one
        product. A rule on a category, a global rule, a formula - these are
        how a shop prices a range, and a change to one of them moves real
        shelf labels. They used to be skipped on the grounds that turning a
        default over a whole range into a revaluation of everything
        underneath is not what the shop means, and that would be true if the
        set of products were the answer. It is not: it is only the set worth
        pricing twice. What ends up on a document is decided afterwards, by
        comparing the price before with the price after and keeping what
        actually moved.

        Applied to an indirect rule - one edited on a list the shop derives
        from - the scope still holds: a rule on a category in the base list
        can only move the derived price of products in that category. It over
        estimates, because a rule on the shop's own list may well win over the
        one that moved, and again the price comparison settles it.
        """
        self.ensure_one()
        if not products:
            return products
        if self.applied_on == "0_product_variant":
            return products & self.product_id
        if self.applied_on == "1_product":
            return products.filtered(
                lambda p: p.product_tmpl_id == self.product_tmpl_id
            )
        if self.applied_on == "2_product_category":
            if not self.categ_id:
                return products
            categories = self.env["product.category"].search(
                [("id", "child_of", self.categ_id.id)]
            )
            return products.filtered(lambda p: p.categ_id in categories)
        return products

    def _l10n_ro_retail_targets(self):
        """``{warehouse: products}`` these rules can move the shelf price of.

        Bounded by what is actually on the shelf. A global rule names the
        whole catalogue, but only the goods the shop holds can be revalued -
        the document has nothing to say about anything else - so the candidate
        set starts from the quants of the retail locations and is narrowed by
        the scope of each rule. That is what keeps a global rule proportionate
        to the assortment of one shop instead of the size of the catalogue.
        """
        mapping = self._l10n_ro_retail_warehouses(self.pricelist_id)
        if not mapping:
            return {}
        warehouses = self.env["stock.warehouse"].browse(
            {w.id for whs in mapping.values() for w in whs}
        )
        on_hand = self._l10n_ro_on_hand_products(warehouses)
        empty = self.env["product.product"]
        targets = {}
        for item in self:
            for warehouse in mapping.get(item.pricelist_id.id, []):
                products = item._l10n_ro_scope_products(
                    on_hand.get(warehouse.id, empty)
                )
                if products:
                    targets[warehouse] = targets.get(warehouse, empty) | products
        return targets

    @api.model
    def _l10n_ro_on_hand_products(self, warehouses):
        """``{warehouse_id: products}`` held in the retail locations, in one read."""
        if not warehouses:
            return {}
        groups = (
            self.env["stock.quant"]
            .sudo()
            ._read_group(
                [
                    ("location_id.warehouse_id", "in", warehouses.ids),
                    ("location_id.l10n_ro_retail", "=", True),
                    ("quantity", ">", 0),
                ],
                groupby=["location_id", "product_id"],
            )
        )
        result = {}
        for location, product in groups:
            warehouse_id = location.warehouse_id.id
            result[warehouse_id] = (
                result.get(warehouse_id, self.env["product.product"]) | product
            )
        return result

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """A new rule has no price from before to be compared against.

        So the comparison is made against what the goods on the shelf carry -
        account 371 against the label, the invariant itself. Comparing against
        nothing instead, as though every price had moved up from zero, put
        every article the rule reaches on a document: harmless once posted,
        because a line whose two sides agree books no entry, but a rule
        covering a whole category handed the shop a draft listing its entire
        assortment to read through.
        """
        items = super().create(vals_list)
        if self.env.context.get("skip_retail_price_change"):
            return items
        targets = items._l10n_ro_retail_targets()
        if targets:
            self.env["l10n.ro.retail.price.change"]._l10n_ro_compare_with_carried(
                targets
            )
        return items

    def write(self, vals):
        if self.env.context.get("skip_retail_price_change") or not (
            TRIGGER_FIELDS & vals.keys()
        ):
            return super().write(vals)
        targets = self._l10n_ro_retail_targets()
        old_snapshot = self._l10n_ro_prices(targets)
        res = super().write(vals)
        # The write may have moved an item onto or off a retail pricelist, or
        # changed what it prices, so the affected set is recomputed rather
        # than reused.
        new_targets = self._l10n_ro_merge_targets(
            targets, self._l10n_ro_retail_targets()
        )
        self._l10n_ro_capture_change(old_snapshot, self._l10n_ro_prices(new_targets))
        return res

    def unlink(self):
        """Deleting a rule moves the shelf price too.

        The label then shows whatever answers next - the rule underneath, or
        the sale price - while 371 still carries the price the deleted rule
        set. That is the same divergence a price edit causes, and it deserves
        the same Proces Verbal. The prices after have to be read once the rule
        is gone, so the targets are carried over from before the delete.
        """
        if self.env.context.get("skip_retail_price_change"):
            return super().unlink()
        targets = self._l10n_ro_retail_targets()
        old_snapshot = self._l10n_ro_prices(targets)
        res = super().unlink()
        self._l10n_ro_capture_change(old_snapshot, self._l10n_ro_prices(targets))
        return res

    @api.model
    def _l10n_ro_merge_targets(self, left, right):
        merged = dict(left)
        for warehouse, products in right.items():
            merged[warehouse] = (
                merged.get(warehouse, self.env["product.product"]) | products
            )
        return merged

    @api.model
    def _l10n_ro_prices(self, targets):
        """Shelf prices for ``{warehouse: products}``, as they stand now.

        One pricelist call per warehouse rather than one per product. A
        product with no rule left on the shop's retail pricelist has no shelf
        price at all; it is left out rather than refused, because this hook
        watches prices, it does not authorise anything, and it must not turn a
        pricelist edit into an error. The shop is stopped later, when it tries
        to move or revalue goods it has no price for.
        """
        result = {}
        for warehouse, products in targets.items():
            prices = products._l10n_ro_get_retail_prices_batch(
                warehouse=warehouse, company=warehouse.company_id
            )
            for product_id, price in prices.items():
                result[(warehouse.id, product_id)] = price
        return result

    @api.model
    def _l10n_ro_capture_change(self, old_snapshot, new_snapshot):
        """Record the shelf prices that actually moved on a draft document."""
        self.env["l10n.ro.retail.price.change"]._l10n_ro_record_moves(
            old_snapshot, new_snapshot
        )
