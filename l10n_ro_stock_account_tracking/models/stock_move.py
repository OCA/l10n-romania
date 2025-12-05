# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "l10n.ro.mixin"]

    l10n_ro_move_track_src_ids = fields.One2many(
        "l10n.ro.stock.move.tracking",
        "dest_move_id",
        string="Romania - Source Tracking",
        readonly=True,
    )
    l10n_ro_move_track_dest_ids = fields.One2many(
        "l10n.ro.stock.move.tracking",
        "src_move_id",
        string="Romania - Destination Tracking",
        readonly=True,
    )

    def _l10n_ro_update_fifo_move(self, fifo_item, move):
        """Updates the move based on FIFO item."""
        res = super()._l10n_ro_update_fifo_move(fifo_item, move)
        if fifo_item.get("move_id"):
            src_move = self.env["stock.move"].browse(fifo_item["move_id"])
            move.l10n_ro_move_track_src_ids = [
                (
                    0,
                    0,
                    {
                        "src_move_id": fifo_item["move_id"],
                        "quantity": fifo_item["quantity"],
                        "value": fifo_item["quantity"]
                        / src_move.remaining_qty
                        * src_move.remaining_value
                        if src_move.remaining_qty
                        else 0,
                    },
                )
            ]
        return res

    def _l10n_ro_update_fifo_split_move_vals(
        self, move, new_move_vals, fifo_item, fifo_quantity
    ):
        """Updates the move vals for a FIFO split move."""
        res = super()._l10n_ro_update_fifo_split_move_vals(
            move, new_move_vals, fifo_item, fifo_quantity
        )
        if fifo_item.get("move_id"):
            src_move = self.env["stock.move"].browse(fifo_item["move_id"])
            new_move_vals["l10n_ro_move_track_src_ids"] = [
                (
                    0,
                    0,
                    {
                        "src_move_id": fifo_item["move_id"],
                        "quantity": fifo_quantity,
                        "value": fifo_quantity
                        / src_move.remaining_qty
                        * src_move.remaining_value
                        if src_move.remaining_qty
                        else 0,
                    },
                )
            ]
        return res
