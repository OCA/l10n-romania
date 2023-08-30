# Copyright (C) 2016 Forest and Biomass Romania
# Copyright (C) 2018 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2019 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models, api


class StockWarehouse(models.Model):
    _name = "stock.warehouse"
    _inherit = ["stock.warehouse", "l10n.ro.mixin"]

    l10n_ro_wh_consume_loc_id = fields.Many2one(
        "stock.location", string="Romania - Consume Location"
    )
    l10n_ro_wh_usage_loc_id = fields.Many2one(
        "stock.location", string="Romania - Usage Giving Location"
    )
    l10n_ro_consume_type_id = fields.Many2one(
        "stock.picking.type", string="Romania - Consume Type"
    )
    l10n_ro_usage_type_id = fields.Many2one(
        "stock.picking.type", string="Romania - Usage Giving Type"
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['l10n_ro_wh_consume_loc_id'] = self.env.ref('l10n_ro_stock.consume_location').id
            vals['l10n_ro_wh_usage_loc_id'] = self.env.ref('l10n_ro_stock.usage_giving_location').id
        return super().create(vals_list)

    def _create_missing_locations(self, vals):
        res = super(StockWarehouse, self)._create_missing_locations(vals)
        for warehouse in self:
            missing_location = {}
            if not warehouse.l10n_ro_wh_consume_loc_id and 'l10n_ro_wh_consume_loc_id' not in vals:
                missing_location['l10n_ro_wh_consume_loc_id'] = self.env.ref('l10n_ro_stock.consume_location').id
            if not warehouse.l10n_ro_wh_usage_loc_id and 'l10n_ro_wh_usage_loc_id' not in vals:
                missing_location['l10n_ro_wh_usage_loc_id'] = self.env.ref('l10n_ro_stock.usage_giving_location').id
            if missing_location:
                warehouse.write(missing_location)
        return res

    def _get_picking_type_update_values(self):
        res = super(StockWarehouse, self)._get_picking_type_update_values()
        if self.is_l10n_ro_record:
            res.update({"l10n_ro_consume_type_id": {}, "l10n_ro_usage_type_id": {}})
        return res

    def _get_picking_type_create_values(self, max_sequence):
        create_data, max_sequence = super(
            StockWarehouse, self
        )._get_picking_type_create_values(max_sequence)
        if self.is_l10n_ro_record:
            create_data.update(
                {
                    "l10n_ro_consume_type_id": {
                        "name": _("Consume"),
                        "code": "internal",
                        "use_create_lots": True,
                        "use_existing_lots": False,
                        "default_location_src_id": self.lot_stock_id.id,
                        "default_location_dest_id": self.l10n_ro_wh_consume_loc_id.id,
                        "sequence": max_sequence + 6,
                        "barcode": self.code.replace(" ", "").upper() + "-CONSUME",
                        "show_reserved": False,
                        "sequence_code": "CONS",
                        "company_id": self.company_id.id,
                    },
                    "l10n_ro_usage_type_id": {
                        "name": _("Usage Giving"),
                        "code": "internal",
                        "use_create_lots": True,
                        "use_existing_lots": False,
                        "default_location_src_id": self.lot_stock_id.id,
                        "default_location_dest_id": self.l10n_ro_wh_usage_loc_id.id,
                        "sequence": max_sequence + 7,
                        "barcode": self.code.replace(" ", "").upper() + "-USAGE",
                        "sequence_code": "USAGE",
                        "company_id": self.company_id.id,
                    },
                }
            )
            max_sequence += 2
        return create_data, max_sequence

    def _get_sequence_values(self, name=False, code=False):
        sequences = super(StockWarehouse, self)._get_sequence_values(
            name=name, code=code
        )
        if self.is_l10n_ro_record:
            sequences.update(
                {
                    "l10n_ro_consume_type_id": {
                        "name": self.name + " " + _("Sequence Consume"),
                        "prefix": self.code + "/CONS/",
                        "padding": 5,
                        "company_id": self.company_id.id,
                    },
                    "l10n_ro_usage_type_id": {
                        "name": self.name + " " + _("Sequence Usage Giving"),
                        "prefix": self.code + "/USAGE/",
                        "padding": 5,
                        "company_id": self.company_id.id,
                    },
                }
            )
        return sequences

    def _update_name_and_code(self, new_name=False, new_code=False):
        res = super(StockWarehouse, self)._update_name_and_code(new_name, new_code)
        ro_whs = self.filtered("is_l10n_ro_record")
        for warehouse in ro_whs:
            sequence_data = warehouse._get_sequence_values()
            warehouse.l10n_ro_consume_type_id.sequence_id.write(
                sequence_data["l10n_ro_consume_type_id"]
            )
            warehouse.l10n_ro_usage_type_id.sequence_id.write(
                sequence_data["l10n_ro_usage_type_id"]
            )
        return res
