# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    origin_ret_move_qty_check = fields.Boolean(compute="_compute_origin_ret_move_qty")
    origin_ret_move_qty = fields.Float(compute="_compute_origin_ret_move_qty")

    @api.depends("quantity")
    def _compute_origin_ret_move_qty(self):
        for line in self:
            mv = line.move_id.sudo()
            if mv.stock_valuation_layer_ids:
                vls = mv.stock_valuation_layer_ids.filtered(
                    lambda sv: sv.remaining_qty > 0
                )
                mv_rem_qty = sum(vls.mapped("remaining_qty"))
                line.origin_ret_move_qty = mv_rem_qty
                line.origin_ret_move_qty_check = mv_rem_qty >= line.quantity
            else:
                line.origin_ret_move_qty = line.quantity
                line.origin_ret_move_qty_check = True
