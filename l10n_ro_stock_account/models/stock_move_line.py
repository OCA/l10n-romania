# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class StockMoveLine(models.Model):
    _name = "stock.move.line"
    _inherit = ["stock.move.line", "l10n.ro.mixin"]

    def _create_correction_svl(self, move, diff):
        """Create the correction layers using the Romanian valued types.

        The standard method calls `_create_in_svl` / `_create_out_svl`
        directly. For Romanian records those methods are no-ops unless the
        `standard` key is in the context, so correcting the quantity of an
        already done move silently created neither a valuation layer nor an
        accounting entry. Here we replay the same decision tree as the
        standard, but with the valued type of the move in the context so the
        layer and the journal entry land on the same accounts as the original
        operation.
        """
        if not move.is_l10n_ro_record:
            return super()._create_correction_svl(move, diff)

        # dropshipping is already handled by `_create_dropshipped_svl`
        if move._is_dropshipped() or move._is_dropshipped_returned():
            return super()._create_correction_svl(move, diff)

        valued_type = move._l10n_ro_get_valued_type()
        if not valued_type:
            return super()._create_correction_svl(move, diff)

        _logger.debug("Correction SVL for move %s (%s): %s", move.id, valued_type, diff)
        move = move.with_context(standard=True, valued_type=valued_type)
        stock_valuation_layers = self.env["stock.valuation.layer"]
        if (move._is_in() and diff > 0) or (move._is_out() and diff < 0):
            move.product_price_update_before_done(forced_qty=diff)
            stock_valuation_layers |= move._create_in_svl(forced_quantity=abs(diff))
            if move.product_id.cost_method in ("average", "fifo"):
                move.product_id._run_fifo_vacuum(move.company_id)
        elif (move._is_in() and diff < 0) or (move._is_out() and diff > 0):
            stock_valuation_layers |= move._create_out_svl(forced_quantity=abs(diff))

        stock_valuation_layers._validate_accounting_entries()
        return stock_valuation_layers
