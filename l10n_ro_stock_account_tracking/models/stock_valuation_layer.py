# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class StockValuationLayer(models.Model):
    _name = "stock.valuation.layer"
    _inherit = ["stock.valuation.layer", "l10n.ro.mixin"]

    l10n_ro_stock_move_line_id = fields.Many2one(
        "stock.move.line", index=True, readonly=True, string="Romania - Stock Move Line"
    )
    l10n_ro_location_id = fields.Many2one(
        "stock.location",
        compute="_compute_l10n_ro_svl_locations_lot",
        store=True,
        index=True,
        string="Romania - Source Location",
    )
    l10n_ro_location_dest_id = fields.Many2one(
        "stock.location",
        compute="_compute_l10n_ro_svl_locations_lot",
        store=True,
        index=True,
        string="Romania - Destination Location",
    )
    l10n_ro_lot_ids = fields.Many2many(
        "stock.lot",
        compute="_compute_l10n_ro_svl_locations_lot",
        store=True,
        index=True,
        string="Romania - Serial Numbers",
    )
    l10n_ro_svl_track_dest_ids = fields.One2many(
        "l10n.ro.stock.valuation.layer.tracking",
        "svl_src_id",
        string="Romania - Source Tracking",
    )
    l10n_ro_svl_track_src_ids = fields.One2many(
        "l10n.ro.stock.valuation.layer.tracking",
        "svl_dest_id",
        string="Romania - Destination Tracking",
    )
    l10n_ro_svl_dest_ids = fields.Many2many(
        "stock.valuation.layer",
        compute="_compute_l10n_ro_svl_tracking",
        string="Romania - Source Valuation",
    )
    l10n_ro_svl_src_ids = fields.Many2many(
        "stock.valuation.layer",
        compute="_compute_l10n_ro_svl_tracking",
        string="Romania - Destination Valuation",
    )
    # cantitate returnata dintr-o iesire
    l10n_ro_qty_returned = fields.Float()

    @api.depends("stock_move_id", "l10n_ro_stock_move_line_id")
    def _compute_l10n_ro_svl_locations_lot(self):
        for svl in self:
            record = (
                svl.l10n_ro_stock_move_line_id
                if svl.l10n_ro_stock_move_line_id
                else svl.stock_move_id
            )
            svl.l10n_ro_location_id = record.location_id
            svl.l10n_ro_location_dest_id = record.location_dest_id
            svl.l10n_ro_lot_ids = (
                record.lot_id if "lot_id" in record._fields else record.lot_ids
            )

    def _compute_l10n_ro_svl_tracking(self):
        for s in self:
            s.l10n_ro_svl_dest_ids = [
                (6, 0, s.l10n_ro_svl_track_dest_ids.mapped("svl_dest_id").ids)
            ]
            s.l10n_ro_svl_src_ids = [
                (6, 0, s.l10n_ro_svl_track_src_ids.mapped("svl_src_id").ids)
            ]

    @api.model
    def _l10n_ro_pre_process_value(self, value):
        """
        Pentru a mapa tracking pe SVL in value pastram o cheie
        'l10n_ro_tracking': [(svl_id, qty).....]
        inainte sa executam .create() curatam dictionarul.
        """
        fields_dict = self._fields.keys()
        return {
            svl_key: svl_value
            for svl_key, svl_value in value.items()
            if svl_key in fields_dict
        }

    def _l10n_ro_post_process(self, value):
        """
        Pentru a mapa l10n_ro_tracking pe SVL in value pastram o cheie
        'l10n_ro_tracking': [(svl_id, qty).....]
        acum este momentul sa mapam sursa, destinatia si cantitatea.
        """

        if value.get("l10n_ro_tracking", None):
            self._l10n_ro_create_tracking(value.get("l10n_ro_tracking"))

    def _l10n_ro_tracking_merge_value(self, svl_id, quantity, value):
        return {
            "svl_src_id": svl_id,
            "quantity": quantity,
            "value": value,
        }

    def _l10n_ro_prepare_tracking_value(self, source_svl_qty):
        svl_tracking_values = []
        for svl_item in source_svl_qty:
            svl_tracking_values.append(self._l10n_ro_tracking_merge_value(*svl_item))
        return svl_tracking_values

    def _l10n_ro_create_tracking(self, source_svl_qty):
        tracking_values = self._l10n_ro_prepare_tracking_value(source_svl_qty)
        svl_tracking_ids = self.env["l10n.ro.stock.valuation.layer.tracking"].create(
            tracking_values
        )
        svl_tracking_ids.write({"svl_dest_id": self.id})
        return svl_tracking_ids
