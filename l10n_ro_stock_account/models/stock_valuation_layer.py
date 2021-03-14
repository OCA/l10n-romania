# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    valued_type = fields.Char()

    def init(self):
        """ This method will compute values for valuation layer valued_type"""
        val_layers = self.search(
            ["|", ("valued_type", "=", False), ("valued_type", "=", "")]
        )
        val_types = self.env["stock.move"]._get_valued_types()
        val_types = [
            val
            for val in val_types
            if val not in ["in", "out", "dropshipped", "dropshipped_returned"]
        ]
        for layer in val_layers:
            if layer.stock_move_id:
                for valued_type in val_types:
                    if getattr(layer.stock_move_id, "_is_%s" % valued_type)():
                        layer.valued_type = valued_type
                        continue

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if "valued_type" not in values and "stock_valuation_layer_id" in values:
                svl = self.env["stock.valuation.layer"].browse(
                    values["stock_valuation_layer_id"]
                )
                if svl:
                    values["valued_type"] = svl.valued_type
        return super(StockValuationLayer, self).create(vals_list)
