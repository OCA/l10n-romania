# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    l10n_ro_origin_ret_move_qty_warn = fields.Boolean(
        compute="_compute_l10n_ro_origin_ret_move_qty"
    )
    l10n_ro_origin_ret_move_qty = fields.Float(
        compute="_compute_l10n_ro_origin_ret_move_qty"
    )

    @api.depends("quantity")
    def _compute_l10n_ro_origin_ret_move_qty(self):
        for line in self:
            mv = line.move_id.sudo()
            if (
                mv.is_l10n_ro_record
                and mv.product_id.cost_method in ("average", "fifo")
                and mv._is_in()
                and mv.stock_valuation_layer_ids
            ):
                svls = mv.stock_valuation_layer_ids.filtered(
                    lambda sv: sv.remaining_qty > 0
                )
                mv_rem_qty = sum(svls.mapped("remaining_qty"))
                line.l10n_ro_origin_ret_move_qty = mv_rem_qty
                line.l10n_ro_origin_ret_move_qty_warn = mv_rem_qty < line.quantity
            else:
                line.l10n_ro_origin_ret_move_qty = line.quantity
                line.l10n_ro_origin_ret_move_qty_warn = False
