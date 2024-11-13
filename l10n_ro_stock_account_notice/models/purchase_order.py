from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _prepare_picking(self):
        vals = super()._prepare_picking()
        picking_type = self.picking_type_id
        if picking_type.l10n_ro_notice_default:
            vals["l10n_ro_notice"] = True

        return vals
