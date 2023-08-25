from odoo import api, fields, models


class Picking(models.Model):
    _inherit = "stock.picking"

    valued_svl = fields.Float(string="Valoare", compute="_compute_valued_svls")

    @api.depends("move_lines.stock_valuation_layer_ids.value")
    def _compute_valued_svls(self):
        for s in self:
            s.valued_svl = sum(s.mapped("move_lines.stock_valuation_layer_ids.value"))
