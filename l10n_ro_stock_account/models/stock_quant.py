# Copyright (C) 2021 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#).


import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.depends("company_id", "location_id", "owner_id", "product_id", "quantity")
    def _compute_value(self):
        quants_with_loc = self.filtered(lambda q: q.location_id)
        for quant in quants_with_loc:
            super(
                StockQuant, quant.with_context(location_id=quant.location_id.id)
            )._compute_value()
        return super(StockQuant, self - quants_with_loc)._compute_value()
