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
            lambda quant: quant.is_l10n_ro_record
            and quant.product_id.cost_method == "fifo"
            and not quant.product_id.lot_valuated
        )
        for quant in ro_fifo_quants:
            quant.value = quant.product_id._run_fifo_value(
                quant.quantity, location=quant.location_id
            )
        return res
