# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class StockQuant(models.Model):
    _name = "stock.quant"
    _inherit = ["stock.quant", "l10n.ro.mixin"]

    l10n_ro_nondeductible_tax_id = fields.Many2one(
        "account.tax",
        string="Non Deductible Tax",
        domain=[("l10n_ro_is_nondeductible", "=", True)],
        copy=False,
    )
    l10n_ro_nondeductible_percent = fields.Selection(
        [("0", "Deductible"), ("50", "50% Nondeductible"), ("100", "Nondeductible")],
        string="Deductibility",
        default="50",
    )

    def _get_inventory_move_values(
        self,
        qty,
        location_id,
        location_dest_id,
        package_id=False,
        package_dest_id=False,
    ):
        res = super()._get_inventory_move_values(
            qty, location_id, location_dest_id, package_id, package_dest_id
        )
        if self.l10n_ro_nondeductible_tax_id:
            nd_tax = self.l10n_ro_nondeductible_tax_id
            nd_perc = self.l10n_ro_nondeductible_percent
            res.update(
                {
                    "l10n_ro_nondeductible_tax_id": nd_tax.id,
                    "l10n_ro_nondeductible_percent": nd_perc,
                }
            )
        return res

    @api.model
    def _get_inventory_fields_create(self):
        """Returns a list of fields user can edit when he want
        to create a quant in `inventory_mode`."""
        res = super()._get_inventory_fields_create()
        res += [
            "l10n_ro_nondeductible_tax_id",
            "l10n_ro_nondeductible_percent",
            "is_l10n_ro_record",
        ]
        return res

    @api.model
    def _get_inventory_fields_write(self):
        """Returns a list of fields user can edit when he want
        to edit a quant in `inventory_mode`."""
        res = super()._get_inventory_fields_write()
        res += [
            "l10n_ro_nondeductible_tax_id",
            "l10n_ro_nondeductible_percent",
            "is_l10n_ro_record",
        ]
        return res

    def _apply_inventory(self, date=None):
        if self.l10n_ro_nondeductible_tax_id:
            self = self.with_context(l10n_ro_exclude_from_stock=True)
        res = super()._apply_inventory(date=date)
        if self.l10n_ro_nondeductible_tax_id:
            self.l10n_ro_nondeductible_tax_id = False
        return res
