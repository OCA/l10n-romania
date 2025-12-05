# Copyright (C) 2025 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "l10n.ro.mixin"]

    def _compute_remaining_qty(self):
        res = super()._compute_remaining_qty()
        ro_fifo_moves = self.filtered(
            lambda move: move.is_l10n_ro_record
            and move.product_id.cost_method == "fifo"
            and not move.product_id.lot_valuated
        )
        if ro_fifo_moves:
            for move in ro_fifo_moves:
                move.remaining_qty = 0
                if move.location_dest_id._should_be_valued():
                    location = move.location_dest_id
                    remaining_by_product = move.product_id._get_remaining_moves_ro(
                        location=location
                    )
                    move.remaining_qty = remaining_by_product.get(
                        move.product_id, {}
                    ).get(move, 0)
        return res

    @api.depends("value", "quantity", "product_id.stock_move_ids.value")
    def _compute_remaining_value(self):
        return super()._compute_remaining_value()

    def _action_done(self, cancel_backorder=False):
        ro_fifo_moves_out = self.filtered(
            lambda m: m._is_out()
            and m.product_id.cost_method == "fifo"
            and not m.origin_returned_move_id
        )
        res = super(StockMove, self - ro_fifo_moves_out)._action_done(
            cancel_backorder=cancel_backorder
        )
        if ro_fifo_moves_out:
            moves_out_fifo_splitted = ro_fifo_moves_out._split_for_fifo_assignment()
            for move in moves_out_fifo_splitted:
                move._set_quantity_done(move.quantity)
                move.picked = True
            for move in ro_fifo_moves_out + moves_out_fifo_splitted:
                move._set_value()
            res += super(
                StockMove, ro_fifo_moves_out + moves_out_fifo_splitted
            )._action_done(cancel_backorder=cancel_backorder)
        return res

    def _set_value(self, correction_quantity=None):
        ro_fifo_out_moves = self.filtered(
            lambda move: move.is_l10n_ro_record
            and move._is_out()
            and move.product_id.cost_method == "fifo"
            and not move.product_id.lot_valuated
        )
        res = super(StockMove, self - ro_fifo_out_moves)._set_value(
            correction_quantity=correction_quantity
        )
        if ro_fifo_out_moves:
            for move in ro_fifo_out_moves:
                value = 0
                for move_line in move.move_line_ids:
                    value += move.product_id._run_fifo_value(
                        move_line.quantity_product_uom,
                        lot=move_line.lot_id,
                        at_date=move.date,
                        location=move_line.location_dest_id,
                    )
                move.value = value
        return res

    def _get_value_from_origin_move(
        self,
        quantity,
        forced_std_price=False,
        at_date=False,
        ignore_manual_update=False,
    ):
        if self.move_orig_ids:
            move_origin = self.move_orig_ids[0]
            origin_data = move_origin._get_value_data(
                forced_std_price=forced_std_price,
                at_date=at_date,
                ignore_manual_update=ignore_manual_update,
            )
            proportion = (
                quantity / origin_data["quantity"] if origin_data["quantity"] else 0
            )
            value = proportion * origin_data["value"]
            return {
                "value": value,
                "quantity": quantity,
                "description": self.env._(
                    "Value based on origin move %(reference)s",
                    reference=self.move_orig_ids.reference,
                ),
            }
        return {}

    def _get_value_from_std_price(self, quantity, std_price=False, at_date=None):
        res = super()._get_value_from_std_price(
            quantity=quantity, std_price=std_price, at_date=at_date
        )
        ro_fifo_move_with_origin = self.filtered(
            lambda move: move.is_l10n_ro_record
            and move.product_id.cost_method == "fifo"
            and not move.product_id.lot_valuated
            and move.move_orig_ids
            and quantity
        )
        if ro_fifo_move_with_origin:
            res = ro_fifo_move_with_origin._get_value_from_origin_move(
                quantity=quantity, at_date=at_date
            )
        return res

    def _split_for_fifo_assignment(self):
        """Splits moves based on FIFO list coming from product _run_fifo."""
        fifo_split_vals_list = []
        for move in self:
            fifo_list = move.product_id.with_context(
                location=move.location_id.ids
            )._run_fifo(move.product_qty, location=move.location_id)
            quantity = move.product_qty
            if fifo_list:
                if fifo_list[0]["quantity"] <= quantity:
                    self._l10n_ro_update_fifo_move(fifo_list[0], move)
                    quantity -= fifo_list[0]["quantity"]
                    fifo_list.pop(0)
            while quantity > 0 and fifo_list:
                fifo_split_vals_list, quantity = self._l10n_ro_process_fifo_split(
                    move, fifo_list, quantity, fifo_split_vals_list
                )
        if fifo_split_vals_list:
            fifo_splitted_moves = self.env["stock.move"].create(fifo_split_vals_list)
            fifo_splitted_moves.write({"state": "assigned"})
            return fifo_splitted_moves
        return self.env["stock.move"]

    @api.model
    def _l10n_ro_update_fifo_move(self, fifo_item, move):
        """Updates the move based on FIFO item."""
        if fifo_item and move:
            move.quantity = fifo_item["quantity"]

    @api.model
    def _l10n_ro_process_fifo_split(
        self, move, fifo_list, quantity, fifo_split_vals_list
    ):
        """Processes the FIFO split for a given move."""
        fifo_item = fifo_list.pop(0)
        fifo_quantity = fifo_item["quantity"]
        new_move_vals_list = move._split(fifo_quantity)
        if new_move_vals_list:
            for new_move_vals in new_move_vals_list:
                self._l10n_ro_update_fifo_split_move_vals(
                    move, new_move_vals, fifo_item, fifo_quantity
                )
        fifo_split_vals_list += new_move_vals_list
        quantity -= fifo_quantity
        return fifo_split_vals_list, quantity

    @api.model
    def _l10n_ro_update_fifo_split_move_vals(
        self, move, new_move_vals, fifo_item, fifo_quantity
    ):
        """Updates the move vals for a FIFO split move."""
        new_move_vals["picking_id"] = move.picking_id.id
        new_move_vals["quantity"] = fifo_quantity
        new_move_vals["date"] = move.date
