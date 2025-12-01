# Copyright (C) 2025 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class StockLot(models.Model):
    _name = "stock.lot"
    _inherit = ["stock.lot", "l10n.ro.mixin"]

    def _compute_value(self):
        """Compute totals of multiple svl related values"""
        ro_fifo_lots = self.filtered(
            lambda lot: lot.is_l10n_ro_record
            and lot.product_id.cost_method == "fifo"
            and lot.product_id.lot_valuated
        )  # noqa E501
        res = super(StockLot, self - ro_fifo_lots)._compute_value()
        if ro_fifo_lots:
            company_id = self.env.company
            ro_fifo_lots.company_currency_id = company_id.currency_id
            at_date = self.env.context.get("to_date")
            for lot in ro_fifo_lots:
                lot.total_value = lot._run_fifo_value(
                    lot.qty_available, at_date=at_date
                )
        return res
