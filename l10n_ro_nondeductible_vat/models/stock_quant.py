# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class StockQuant(models.Model):
    _name = "stock.quant"
    _inherit = ["stock.quant", "l10n.ro.mixin"]

    l10n_ro_nondeductible_tax_id = fields.Many2one(
        "account.tax", domain=[("l10n_ro_is_nondeductible", "=", True)], copy=False
    )

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, out=False):
        res = super()._get_inventory_move_values(
            qty, location_id, location_dest_id, out
        )
        res["l10n_ro_nondeductible_tax_id"] = (
            self.l10n_ro_nondeductible_tax_id
            and self.l10n_ro_nondeductible_tax_id.id
            or None
        )
        return res

    @api.model
    def _get_inventory_fields_create(self):
        """Returns a list of fields user can edit when he want
        to create a quant in `inventory_mode`."""
        res = super()._get_inventory_fields_create()
        res += ["l10n_ro_nondeductible_tax_id", "is_l10n_ro_record"]
        return res

    @api.model
    def _get_inventory_fields_write(self):
        """Returns a list of fields user can edit when he want
        to edit a quant in `inventory_mode`."""
        res = super()._get_inventory_fields_write()
        res += ["l10n_ro_nondeductible_tax_id", "is_l10n_ro_record"]
        return res

    def _apply_inventory(self):
        res = super()._apply_inventory()
        self.l10n_ro_nondeductible_tax_id = False
        return res
