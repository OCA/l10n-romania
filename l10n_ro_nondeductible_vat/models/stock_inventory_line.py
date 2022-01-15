# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    nondeductible_tax_id = fields.Many2one(
        "account.tax", domain=[("is_nondeductible", "=", True)], copy=False
    )

    def _get_move_values(self, qty, location_id, location_dest_id, out):
        res = super(InventoryLine, self)._get_move_values(
            qty, location_id, location_dest_id, out
        )
        res["nondeductible_tax_id"] = (
            self.nondeductible_tax_id and self.nondeductible_tax_id.id or None
        )
        return res
