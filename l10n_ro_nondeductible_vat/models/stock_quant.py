# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    nondeductible_tax_id = fields.Many2one(
        "account.tax", domain=[("is_nondeductible", "=", True)], copy=False
    )

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, out=False):
        res = super()._get_inventory_move_values(
            qty, location_id, location_dest_id, out
        )
        res["nondeductible_tax_id"] = (
            self.nondeductible_tax_id and self.nondeductible_tax_id.id or None
        )
        return res

    @api.model
    def _get_inventory_fields_create(self):
        fields = super()._get_inventory_fields_create()
        return fields + ["nondeductible_tax_id"]

    @api.model
    def _get_inventory_fields_write(self):
        fields = super()._get_inventory_fields_write()
        return fields + ["nondeductible_tax_id"]

    def _apply_inventory(self):
        res = super()._apply_inventory()
        self.nondeductible_tax_id = False
        return res
