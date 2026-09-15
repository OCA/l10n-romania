# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare

TRIGGER_FIELDS = {
    "fixed_price",
    "compute_price",
    "applied_on",
    "product_id",
    "product_tmpl_id",
    "pricelist_id",
    # A promotion is a shelf price too. Editing its window can make it
    # effective, or stop it being effective, right now - and then the label
    # changes with it. What this cannot catch is the day a future window
    # opens on its own: nothing is written then, and the price a pricelist
    # answers with simply becomes another one. See the module description.
    "date_start",
    "date_end",
    # The rule for quantity 1 is the one on the label.
    "min_quantity",
}


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    def _l10n_ro_affected_products(self):
        """Products this item applies to.

        Only items with ``compute_price='fixed'`` and ``applied_on`` in
        per-product / per-template are followed automatically. For category,
        global or formula items the shop has to raise the Proces Verbal by hand:
        those rules are defaults over a whole range, and turning each of them
        into a revaluation of every product underneath is almost never what the
        shop means.
        """
        self.ensure_one()
        if self.compute_price != "fixed":
            return self.env["product.product"]
        if self.applied_on == "0_product_variant" and self.product_id:
            return self.product_id
        if self.applied_on == "1_product" and self.product_tmpl_id:
            return self.product_tmpl_id.product_variant_ids
        return self.env["product.product"]

    @api.model
    def _l10n_ro_retail_pricelist_ids(self, items):
        """Retail pricelists among ``items``, mapped to their warehouses.

        Resolved once for the whole batch. Asking per item meant a pricelist
        import of a few thousand rows ran one warehouse search, one price
        lookup and one quant search per row - the reason a routine price update
        could take minutes.
        """
        pricelists = items.pricelist_id
        if not pricelists:
            return {}
        warehouses = self.env["stock.warehouse"].search(
            [
                ("l10n_ro_retail", "=", True),
                ("l10n_ro_retail_pricelist_id", "in", pricelists.ids),
            ]
        )
        mapping = {}
        for warehouse in warehouses:
            mapping.setdefault(warehouse.l10n_ro_retail_pricelist_id.id, []).append(
                warehouse
            )
        return mapping

    def _l10n_ro_retail_items(self):
        """The subset of ``self`` that can move a shelf price."""
        mapping = self._l10n_ro_retail_pricelist_ids(self)
        if not mapping:
            return self.browse()
        return self.filtered(lambda item: item.pricelist_id.id in mapping)

    @api.model_create_multi
    def create(self, vals_list):
        items = super().create(vals_list)
        if self.env.context.get("skip_retail_price_change"):
            return items
        retail_items = items._l10n_ro_retail_items()
        if retail_items:
            self._l10n_ro_capture_change({}, retail_items._l10n_ro_snapshot())
        return items

    def write(self, vals):
        if self.env.context.get("skip_retail_price_change") or not (
            TRIGGER_FIELDS & vals.keys()
        ):
            return super().write(vals)
        retail_items = self._l10n_ro_retail_items()
        if not retail_items:
            return super().write(vals)
        old_snapshot = retail_items._l10n_ro_snapshot()
        res = super().write(vals)
        # The write may have moved an item onto or off a retail pricelist, so
        # the affected set is recomputed rather than reused.
        affected = retail_items | self._l10n_ro_retail_items()
        self._l10n_ro_capture_change(old_snapshot, affected._l10n_ro_snapshot())
        return res

    def unlink(self):
        """Deleting a rule moves the shelf price too.

        The label then shows whatever answers next - the rule underneath, or
        the sale price - while 371 still carries the price the deleted rule
        set. That is the same divergence a price edit causes, and it deserves
        the same Proces Verbal. The prices after have to be read once the rule
        is gone, so the keys are carried over from the snapshot taken before.
        """
        if self.env.context.get("skip_retail_price_change"):
            return super().unlink()
        retail_items = self._l10n_ro_retail_items()
        if not retail_items:
            return super().unlink()
        old_snapshot = retail_items._l10n_ro_snapshot()
        res = super().unlink()
        self._l10n_ro_capture_change(
            old_snapshot, self._l10n_ro_prices_for_keys(set(old_snapshot))
        )
        return res

    def _l10n_ro_snapshot(self):
        """Shelf price per ``(warehouse, product)`` for the items in ``self``."""
        mapping = self._l10n_ro_retail_pricelist_ids(self)
        keys = set()
        for item in self:
            for warehouse in mapping.get(item.pricelist_id.id, []):
                for product in item._l10n_ro_affected_products():
                    keys.add((warehouse.id, product.id))
        return self._l10n_ro_prices_for_keys(keys)

    @api.model
    def _l10n_ro_prices_for_keys(self, keys):
        """Shelf prices for ``(warehouse, product)`` keys, as they stand now.

        A product with no rule left on the shop's retail pricelist has no
        shelf price at all, and asking for one raises. That is the right
        answer when goods are about to move, and the wrong one here: this
        hook watches prices, it does not authorise anything, and it must not
        turn a pricelist edit into an error. Such a key is simply left out -
        the shop is stopped later, when it tries to move or revalue goods it
        has no price for.
        """
        Warehouse = self.env["stock.warehouse"]
        Product = self.env["product.product"]
        result = {}
        for warehouse_id, product_id in keys:
            warehouse = Warehouse.browse(warehouse_id)
            try:
                result[(warehouse_id, product_id)] = Product.browse(
                    product_id
                )._l10n_ro_get_retail_prices(
                    warehouse=warehouse, company=warehouse.company_id
                )
            except UserError:
                continue
        return result

    @api.model
    def _l10n_ro_capture_change(self, old_snapshot, new_snapshot):
        """Raise one draft Proces Verbal per warehouse for the products whose
        shelf price actually moved and that are actually on the shelf."""
        keys = set(old_snapshot) | set(new_snapshot)
        if not keys:
            return
        empty = {"price_with_vat": 0.0, "price_without_vat": 0.0, "vat": 0.0}
        Warehouse = self.env["stock.warehouse"]
        Product = self.env["product.product"]
        Doc = self.env["l10n.ro.retail.price.change"].sudo()

        moved = []
        for wh_id, product_id in keys:
            warehouse = Warehouse.browse(wh_id)
            old = old_snapshot.get((wh_id, product_id)) or empty
            new = new_snapshot.get((wh_id, product_id)) or empty
            rounding = warehouse.company_id.currency_id.rounding
            if (
                float_compare(
                    old["price_with_vat"],
                    new["price_with_vat"],
                    precision_rounding=rounding,
                )
                == 0
            ):
                continue
            moved.append((warehouse, Product.browse(product_id), old, new))
        if not moved:
            return

        # One quant read for the whole batch instead of one per product.
        quants = (
            self.env["stock.quant"]
            .sudo()
            ._read_group(
                [
                    ("product_id", "in", [p.id for _w, p, _o, _n in moved]),
                    (
                        "location_id.warehouse_id",
                        "in",
                        [w.id for w, _p, _o, _n in moved],
                    ),
                    ("location_id.l10n_ro_retail", "=", True),
                    ("quantity", ">", 0),
                ],
                groupby=["product_id", "location_id"],
                aggregates=["quantity:sum"],
            )
        )
        on_hand = {}
        for product, location, qty in quants:
            on_hand.setdefault((location.warehouse_id.id, product.id), []).append(
                (location, qty)
            )

        per_warehouse = {}
        for warehouse, product, _old, new in moved:
            for location, qty in on_hand.get((warehouse.id, product.id), []):
                per_warehouse.setdefault(warehouse, []).append(
                    {
                        "product_id": product.id,
                        "location_id": location.id,
                        "quantity": qty,
                        # The old side comes from what the stock carries, not
                        # from the price it used to be quoted at: if the two
                        # had drifted apart, this settles both at once.
                        "new_price_with_vat": new["price_with_vat"],
                    }
                )
        for warehouse, line_vals in per_warehouse.items():
            Doc.create(
                {
                    "warehouse_id": warehouse.id,
                    "company_id": warehouse.company_id.id,
                    "date": fields.Date.context_today(self),
                    "auto_created": True,
                    "line_ids": [Command.create(v) for v in line_vals],
                    "notes": self.env._(
                        "<p>Auto-generated from a change on pricelist %(pl)s.</p>",
                        pl=warehouse.l10n_ro_retail_pricelist_id.display_name,
                    ),
                }
            )
