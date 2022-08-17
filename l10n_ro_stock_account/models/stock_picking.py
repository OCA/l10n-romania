# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "l10n.ro.mixin"]

    def _action_done(self):
        # if is a reception form po, we will send to create invoice
        # is a valued reception with prices form invoice
        res = super()._action_done()
        if (
            len(self) == 1
            and self.is_l10n_ro_record
            and self.purchase_id
            and self.move_lines.filtered(
                lambda r: r.quantity_done and r.product_id.valuation == "real_time"
            )
            and not self.move_lines.stock_valuation_layer_ids  # is not a notice
        ):
            return self.purchase_id.action_create_invoice()
        return res

    def _is_dropshipped(self):
        if not self.is_l10n_ro_record:
            return False

        self.ensure_one()
        return (
            self.location_id.usage == "supplier"
            and self.location_dest_id.usage == "customer"
        )

    def _is_dropshipped_returned(self):
        if not self.is_l10n_ro_record:
            return super()._is_dropshipped()

        self.ensure_one()
        return (
            self.location_id.usage == "customer"
            and self.location_dest_id.usage == "supplier"
        )
