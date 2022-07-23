# Copyright (C) 2022 Dakai Soft
# -*- coding: utf-8 -*-
from odoo import fields, models


class SVLTracking(models.Model):
    _name = "stock.valuation.layer.tracking"
    _description = "Tracking layer stock valuation"
    _rec_name = "svl_dest_id"
    
    svl_dest_id = fields.Many2one("stock.valuation.layer")
    svl_src_id = fields.Many2one("stock.valuation.layer")
    quantity = fields.Float()