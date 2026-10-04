# Copyright (C) 2022 Dakai Soft
from odoo import fields, models


class SVLTracking(models.Model):
    _name = "l10n.ro.stock.move.tracking"
    _description = "Romania - Stock Move Tracking"
    _rec_name = "dest_move_id"

    src_move_id = fields.Many2one(
        "stock.move", string="Source Move", required=True, readonly=True
    )
    dest_move_id = fields.Many2one(
        "stock.move", string="Destination Move", required=True, readonly=True
    )
    quantity = fields.Float()
    value = fields.Float()
