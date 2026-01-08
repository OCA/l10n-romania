# ©  2015-2018 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        vals["ref"] = self.pos_reference
        return vals

    def action_pos_order_invoice(self):
        return super(
            PosOrder, self.with_context(allowed_change_product=True)
        ).action_pos_order_invoice()
