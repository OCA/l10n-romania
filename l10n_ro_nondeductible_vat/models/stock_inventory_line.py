# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class InventoryLine(models.Model):
    _name = "stock.inventory.line"
    _inherit = ["stock.inventory.line", "l10n.ro.mixin"]

    l10n_ro_nondeductible_tax_id = fields.Many2one(
        "account.tax", domain=[("is_nondeductible", "=", True)], copy=False
    )

    def _get_move_values(self, qty, location_id, location_dest_id, out):
        res = super(InventoryLine, self)._get_move_values(
            qty, location_id, location_dest_id, out
        )
        if self.is_l10n_ro_record:
            res["l10n_ro_nondeductible_tax_id"] = (
                self.l10n_ro_nondeductible_tax_id
                and self.l10n_ro_nondeductible_tax_id.id
                or None
            )
        return res
