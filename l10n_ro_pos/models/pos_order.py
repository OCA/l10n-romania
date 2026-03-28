# ©  2015-2018 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"
    _name = "pos.order"
    _inherit = ["pos.order", "l10n.ro.mixin"]

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        if self.is_l10n_ro_record:
            vals["ref"] = self.pos_reference
        return vals
