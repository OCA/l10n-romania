# Copyright (C) 2021 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#).


import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _name = "stock.quant"
    _inherit = ["stock.quant", "l10n.ro.mixin"]

    @api.depends(
        "company_id", "location_id", "owner_id", "product_id", "quantity", "lot_id"
    )
    def _compute_value(self):
        ro_quants = self.filtered(lambda quant: quant.is_l10n_ro_record)
        super(StockQuant, self - ro_quants)._compute_value()
        quants_with_loc = ro_quants.filtered(lambda q: q.location_id)
        for quant in quants_with_loc:
            quant = quant.with_context(
                location_id=quant.location_id.id, lot_id=quant.lot_id
            )
            super(StockQuant, quant)._compute_value()
