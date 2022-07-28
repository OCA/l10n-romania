# Copyright (C) 2022 Dakai Soft
# -*- coding: utf-8 -*-
from odoo import api, fields, models

class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    stock_move_line_id = fields.Many2one("stock.move.line")
    svl_track_dest_ids = fields.One2many("stock.valuation.layer.tracking", 'svl_src_id')
    svl_track_src_ids = fields.One2many("stock.valuation.layer.tracking", 'svl_dest_id')
    svl_dest_ids = fields.Many2many("stock.valuation.layer", compute="_computeSrcDest")
    svl_src_ids = fields.Many2many("stock.valuation.layer", compute="_computeSrcDest")


    def _computeSrcDest(self):
        for s in self:
            s.svl_dest_ids = [(6, 0, s.svl_track_dest_ids.mapped("svl_dest_id").ids)]
            s.svl_src_ids = [(6, 0, s.svl_track_src_ids.mapped("svl_src_id").ids)]

    @api.model
    def _pre_process_value(self, value):
        """
        Pentru a mapa tracking pe SVL in value pastram o cheie
        'tracking': [(svl_id, qty).....]
        inainte sa executam .create() curatam dictionarul.
        """
        fields_dict = self._fields.keys()
        return {svl_key:svl_value for svl_key, svl_value in value.items() if svl_key in fields_dict}

    def _post_process(self, value):
        """
        Pentru a mapa tracking pe SVL in value pastram o cheie
        'tracking': [(svl_id, qty).....]
        acum este momentul sa mapam sursa, destinatia si cantitatea.
        """

        if value.get('tracking', None):
            self._create_tracking(value.get('tracking'))

    def _tracking_merge_value(self, svl_id, quantity, value):
        return {
            'svl_src_id': svl_id,
            'quantity': quantity,
            'value': value,
            }

    def _prepare_tracking_value(self, source_svl_qty):
        svl_tracking_values = []
        for svl_item in source_svl_qty:
            svl_tracking_values.append(self._tracking_merge_value(*svl_item))
        return svl_tracking_values

    def _create_tracking(self, source_svl_qty):
        tracking_values = self._prepare_tracking_value(source_svl_qty)
        svl_tracking_ids = self.env['stock.valuation.layer.tracking'].create(tracking_values)
        svl_tracking_ids.write({'svl_dest_id':self.id})
        return svl_tracking_ids
