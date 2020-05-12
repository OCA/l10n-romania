# Copyright (C) 2016 Forest and Biomass Romania
# Copyright (C) 2018 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2019 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    wh_consume_loc_id = fields.Many2one("stock.location", "Consume Location")
    wh_usage_loc_id = fields.Many2one("stock.location", "Usage Giving Location")
    consume_type_id = fields.Many2one("stock.picking.type", "Consume Type")
    usage_type_id = fields.Many2one("stock.picking.type", "Usage Giving Type")

    def _get_locations_values(self, vals, code=False):
        sub_locations = super(StockWarehouse, self)._get_locations_values(vals, code)
        code = vals.get("code") or code or ""
        code = code.replace(" ", "").upper()
        company_id = vals.get(
            "company_id", self.default_get(["company_id"])["company_id"]
        )
        sub_locations.update(
            {
                "wh_consume_loc_id": {
                    "name": _("Consume"),
                    "active": True,
                    "usage": "consume",
                    "barcode": self._valid_barcode(code + "-CONSUME", company_id),
                },
                "wh_usage_loc_id": {
                    "name": _("Usage"),
                    "active": True,
                    "usage": "usage_giving",
                    "barcode": self._valid_barcode(code + "-USAGE", company_id),
                },
            }
        )
        return sub_locations

    def _get_picking_type_update_values(self):
        res = super(StockWarehouse, self)._get_picking_type_update_values()
        res.update({"consume_type_id": {}, "usage_type_id": {}})
        return res

    def _get_picking_type_create_values(self, max_sequence):
        create_data, max_sequence = super(
            StockWarehouse, self
        )._get_picking_type_create_values(max_sequence)
        create_data.update(
            {
                "consume_type_id": {
                    "name": _("Consume"),
                    "code": "internal",
                    "use_create_lots": True,
                    "use_existing_lots": False,
                    "default_location_src_id": self.lot_stock_id.id,
                    "default_location_dest_id": self.wh_consume_loc_id.id,
                    "sequence": max_sequence + 6,
                    "barcode": self.code.replace(" ", "").upper() + "-CONSUME",
                    "show_reserved": False,
                    "sequence_code": "CONS",
                    "company_id": self.company_id.id,
                },
                "usage_type_id": {
                    "name": _("Usage Giving"),
                    "code": "internal",
                    "use_create_lots": True,
                    "use_existing_lots": False,
                    "default_location_src_id": self.lot_stock_id.id,
                    "default_location_dest_id": self.wh_usage_loc_id.id,
                    "sequence": max_sequence + 7,
                    "barcode": self.code.replace(" ", "").upper() + "-USAGE",
                    "sequence_code": "USAGE",
                    "company_id": self.company_id.id,
                },
            }
        )
        max_sequence += 2
        return create_data, max_sequence

    def _get_sequence_values(self):
        sequences = super(StockWarehouse, self)._get_sequence_values()
        sequences.update(
            {
                "consume_type_id": {
                    "name": self.name + " " + _("Sequence Consume"),
                    "prefix": self.code + "/CONS/",
                    "padding": 5,
                    "company_id": self.company_id.id,
                },
                "usage_type_id": {
                    "name": self.name + " " + _("Sequence Usage Giving"),
                    "prefix": self.code + "/USAGE/",
                    "padding": 5,
                    "company_id": self.company_id.id,
                },
            }
        )
        return sequences

    def _update_name_and_code(self, new_name=False, new_code=False):
        super(StockWarehouse, self)._update_name_and_code(new_name, new_code)
        for warehouse in self:
            sequence_data = warehouse._get_sequence_values()
            warehouse.consume_type_id.sequence_id.write(
                sequence_data["consume_type_id"]
            )
            warehouse.usage_type_id.sequence_id.write(sequence_data["usage_type_id"])
