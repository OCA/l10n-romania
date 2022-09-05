# Copyright (C) 2022 cbssolutions.ro
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_invoice(self):
        # from invoiced products we are getting coresponding the notice picking
        # to set in invoice as l10n_ro_bill_for_pickings_ids
        invoice_vals = super()._prepare_invoice()
        pickings = self.picking_ids.filtered(
            lambda r: r.l10n_ro_notice
            and r.state == "done"
            and not r.l10n_ro_notice_invoice_id
        )
        if pickings:
            invoice_vals["l10n_ro_invoice_for_pickings_ids"] = [(6, 0, pickings.ids)]
        return invoice_vals
