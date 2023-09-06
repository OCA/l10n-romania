# ©  2015-2018 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def button_dummy(self):
        return True

    def _prepare_invoice(self):
        res = super(PosOrder, self)._prepare_invoice()
        res["reference"] = self.pos_reference
        res["pos_ref"] = self.pos_reference
        return res

    def action_pos_order_invoice(self):
        return super(
            PosOrder, self.with_context(allowed_change_product=True)
        ).action_pos_order_invoice()
