# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import Command, api, fields, models
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    def _l10n_ro_affected_products(self):
        """Products this item applies to.

        Only items with ``compute_price='fixed'`` and ``applied_on`` in
        per-product / per-template are supported automatically. For
        category / global / formula items, the user must create a
        Proces Verbal manually.
        """
        self.ensure_one()
        if self.compute_price != "fixed":
            return self.env["product.product"]
        if self.applied_on == "0_product_variant" and self.product_id:
            return self.product_id
        if self.applied_on == "1_product" and self.product_tmpl_id:
            return self.product_tmpl_id.product_variant_ids
        return self.env["product.product"]

    def _l10n_ro_affected_warehouses(self):
        return self.env["stock.warehouse"].search(
            [
                ("l10n_ro_retail", "=", True),
                ("l10n_ro_retail_pricelist_id", "=", self.pricelist_id.id),
            ]
        )

    @api.model_create_multi
    def create(self, vals_list):
        items = super().create(vals_list)
        if self.env.context.get("skip_retail_price_change"):
            return items
        for item in items:
            item._l10n_ro_capture_change(old_snapshot={})
        return items

    def write(self, vals):
        if self.env.context.get("skip_retail_price_change"):
            return super().write(vals)
        triggers = {
            "fixed_price",
            "compute_price",
            "applied_on",
            "product_id",
            "product_tmpl_id",
            "pricelist_id",
        }
        if not triggers.intersection(vals.keys()):
            return super().write(vals)
        snapshots = {item.id: item._l10n_ro_snapshot() for item in self}
        res = super().write(vals)
        for item in self:
            item._l10n_ro_capture_change(old_snapshot=snapshots.get(item.id, {}))
        return res

    def _l10n_ro_snapshot(self):
        """Capture (per-unit) retail prices for each (warehouse, product)
        pair affected by this item, before a modification."""
        result = {}
        for wh in self._l10n_ro_affected_warehouses():
            for product in self._l10n_ro_affected_products():
                prices = product.product_tmpl_id._l10n_ro_get_retail_prices(
                    warehouse=wh, company=wh.company_id
                )
                result[(wh.id, product.id)] = prices
        return result

    def _l10n_ro_capture_change(self, old_snapshot):
        """Generate one draft Proces Verbal per warehouse for the products
        whose retail price actually moved."""
        new_snapshot = self._l10n_ro_snapshot()
        keys = set(old_snapshot) | set(new_snapshot)
        Quant = self.env["stock.quant"]
        Doc = self.env["l10n.ro.retail.price.change"].sudo()
        per_warehouse = {}
        for wh_id, product_id in keys:
            wh = self.env["stock.warehouse"].browse(wh_id)
            product = self.env["product.product"].browse(product_id)
            old = old_snapshot.get((wh_id, product_id)) or {
                "price_with_vat": 0.0,
                "price_without_vat": 0.0,
                "vat": 0.0,
            }
            new = new_snapshot.get((wh_id, product_id)) or {
                "price_with_vat": 0.0,
                "price_without_vat": 0.0,
                "vat": 0.0,
            }
            currency = wh.company_id.currency_id
            if (
                float_compare(
                    old["price_with_vat"],
                    new["price_with_vat"],
                    precision_rounding=currency.rounding,
                )
                == 0
            ):
                continue
            quants = Quant.search(
                [
                    ("company_id", "=", wh.company_id.id),
                    ("location_id.l10n_ro_retail", "=", True),
                    ("location_id.warehouse_id", "=", wh.id),
                    ("product_id", "=", product.id),
                    ("quantity", ">", 0),
                ]
            )
            if not quants:
                continue
            grouped = {}
            for q in quants:
                grouped.setdefault(q.location_id, 0.0)
                grouped[q.location_id] += q.quantity
            for location, qty in grouped.items():
                cost_unit = product.with_company(wh.company_id).standard_price
                per_warehouse.setdefault(wh, []).append(
                    {
                        "product_id": product.id,
                        "location_id": location.id,
                        "quantity": qty,
                        "cost_unit": cost_unit,
                        "old_price_with_vat": old["price_with_vat"],
                        "new_price_with_vat": new["price_with_vat"],
                    }
                )
        for wh, line_vals in per_warehouse.items():
            Doc.create(
                {
                    "warehouse_id": wh.id,
                    "company_id": wh.company_id.id,
                    "date": fields.Date.context_today(self),
                    "auto_created": True,
                    "line_ids": [Command.create(v) for v in line_vals],
                    "notes": self.env._(
                        "<p>Auto-generated from pricelist change "
                        "(item id %(item)s on %(pl)s).</p>",
                        item=self.id,
                        pl=self.pricelist_id.display_name,
                    ),
                }
            )
