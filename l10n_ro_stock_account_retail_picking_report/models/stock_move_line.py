# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models

# Keys the QWeb rows read. Every aggregated row must carry all of them,
# whether or not the loop below reaches it: the template dereferences them
# unconditionally, and its own guard sits at picking level while the loop works
# at move line level. A row the loop skips prints zeros, which is the right
# figure - that move loaded no markup.
RETAIL_KEYS = (
    "l10n_ro_retail_cost_unit",
    "l10n_ro_retail_cost_subtotal",
    "l10n_ro_retail_markup",
    "l10n_ro_retail_markup_percent",
    "l10n_ro_retail_price_no_vat_unit",
    "l10n_ro_retail_vat",
    "l10n_ro_retail_price_unit",
    "l10n_ro_retail_price_total",
)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _get_aggregated_product_quantities(self, **kwargs):
        """Add the retail split of each printed row.

        The amounts come from the markup ledger rows the move produced, so the
        note prints what was actually loaded on 378 and 4428 for this
        reception. Recomputing from the pricelist would print a different
        number every time the shelf price moved after the fact.

        The ledger holds one row per move; the report prints move lines. Each
        line therefore takes its share of the move, because the report is also
        called with ``self`` narrowed to a single package or to the unpackaged
        lines, and attributing the whole move to each of those sections would
        print the reception several times over.
        """
        aggregated_lines = super()._get_aggregated_product_quantities(**kwargs)
        for agg_line in aggregated_lines.values():
            for key in RETAIL_KEYS:
                agg_line.setdefault(key, 0.0)

        for move_line in self:
            move = move_line.move_id
            if not move.location_dest_id.l10n_ro_retail:
                continue
            rows = move.l10n_ro_retail_markup_line_ids.filtered(
                lambda row: row.quantity > 0
            )
            if not rows:
                continue
            line_key = self._get_aggregated_properties(move_line=move_line)["line_key"]
            agg_line = aggregated_lines.get(line_key)
            if not agg_line:
                continue
            share = move_line.quantity / move.product_qty if move.product_qty else 0.0
            agg_line["l10n_ro_retail_cost_subtotal"] += abs(move.value) * share
            agg_line["l10n_ro_retail_markup"] += sum(rows.mapped("markup")) * share
            agg_line["l10n_ro_retail_vat"] += sum(rows.mapped("vat")) * share

        for agg_line in aggregated_lines.values():
            qty = agg_line.get("quantity") or 0.0
            cost = agg_line["l10n_ro_retail_cost_subtotal"]
            markup = agg_line["l10n_ro_retail_markup"]
            vat = agg_line["l10n_ro_retail_vat"]
            agg_line["l10n_ro_retail_cost_unit"] = cost / qty if qty else 0.0
            agg_line["l10n_ro_retail_markup_percent"] = (
                markup / cost * 100 if cost else 0.0
            )
            agg_line["l10n_ro_retail_price_no_vat_unit"] = (
                (cost + markup) / qty if qty else 0.0
            )
            agg_line["l10n_ro_retail_price_total"] = cost + markup + vat
            agg_line["l10n_ro_retail_price_unit"] = (
                agg_line["l10n_ro_retail_price_total"] / qty if qty else 0.0
            )
        return aggregated_lines
