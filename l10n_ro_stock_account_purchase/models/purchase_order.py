# Copyright (C) 2022 cbssolutions.ro
from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _prepare_invoice(self):
        # if the invoice was created from a reception picking we ar setting the
        # l10n_ro_bill_for_picking
        invoice_vals = super()._prepare_invoice()
        inv_for_reception_picking = self._context.get("inv_for_reception_picking")
        if inv_for_reception_picking:
            invoice_vals["l10n_ro_bill_for_picking"] = inv_for_reception_picking
        return invoice_vals
