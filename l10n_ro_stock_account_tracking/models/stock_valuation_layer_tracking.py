# Copyright (C) 2022 Dakai Soft
from odoo import fields, models


class SVLTracking(models.Model):
    _name = "l10n.ro.stock.valuation.layer.tracking"
    _description = "Romania - Tracking layer stock valuation"
    _rec_name = "svl_dest_id"

    svl_dest_id = fields.Many2one("stock.valuation.layer")
    svl_src_id = fields.Many2one("stock.valuation.layer")
    quantity = fields.Float()
    value = fields.Float()
