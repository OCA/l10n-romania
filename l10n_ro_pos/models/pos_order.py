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

    def _prepare_invoice_line(self, order_line):
        res = super(PosOrder, self)._prepare_invoice_line(order_line)
        # se va determina contul de venituri in functie de produs si de locatie
        return res
