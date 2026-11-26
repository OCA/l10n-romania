# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _l10n_ro_retail_nir_values(self):
        """Retail split of this move for its NIR row: markup, deferred VAT and
        the shelf price.

        The amounts come from the markup ledger rows the move produced, so the
        note prints what was actually loaded on 378 and 4428 for this
        reception, not a recomputation from the pricelist that would move with
        the shelf price after the fact. The NIR prints one row per move, so the
        whole of the move's ledger belongs to the row - no per-line share is
        needed here (that is the move-line report's concern)."""
        self.ensure_one()
        rows = self.l10n_ro_retail_markup_line_ids.filtered(
            lambda row: row.quantity > 0
        )
        cost = sum(rows.mapped("cost"))
        markup = sum(rows.mapped("markup"))
        vat = sum(rows.mapped("vat"))
        retail_value = sum(rows.mapped("retail_value"))
        qty = self._l10n_ro_retail_qty()
        return {
            "cost": cost,
            "markup": markup,
            "markup_percent": (markup / cost * 100) if cost else 0.0,
            "vat": vat,
            "retail_price_no_vat_unit": ((cost + markup) / qty) if qty else 0.0,
            "retail_price_vat_unit": (retail_value / qty) if qty else 0.0,
            "retail_value": retail_value,
        }
