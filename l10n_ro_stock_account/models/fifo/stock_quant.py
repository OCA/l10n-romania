# Copyright (C) 2025 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _name = "stock.quant"
    _inherit = ["stock.quant", "l10n.ro.mixin"]

    def _compute_value(self):
        res = super()._compute_value()
        ro_fifo_quants = self.filtered(
            lambda quant: quant.company_id.fifo_per_location
            and quant.product_id.cost_method == "fifo"
            and not quant.product_id.lot_valuated
        )
        if not ro_fifo_quants:
            return res
        # Share a request-scoped cache across all FIFO stack lookups
        # in this batch (e.g. an Inventory Valuation report with many quants
        # for the same (product, location) pair).
        cache = self.env.context.get("fifo_stack_cache")
        if cache is None:
            cache = {}
            ro_fifo_quants = ro_fifo_quants.with_context(fifo_stack_cache=cache)
        for quant in ro_fifo_quants:
            quant.value = quant.product_id._run_fifo_value(
                quant.quantity, location=quant.location_id
            )
        return res
