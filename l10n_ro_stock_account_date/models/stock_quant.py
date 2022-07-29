# Copyright (C) 2022 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, out=False):
        # Inherit to set date as accounting_date from inventoried quant
        self.ensure_one()
        vals = super()._get_inventory_move_values(
            qty, location_id, location_dest_id, out
        )
        if self.accounting_date:
            vals["date"] = self.accounting_date
        return vals

    def _apply_inventory(self):
        # If accounting date is set, set also inventory date
        res = super()._apply_inventory()
        for quant in self:
            if quant.accounting_date:
                quant.inventory_date = quant.accounting_date
        return res
