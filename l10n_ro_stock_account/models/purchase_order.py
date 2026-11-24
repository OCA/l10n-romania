# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _compute_invoice(self):
        # The stock entries of a reception carry the purchase line too (see
        # ``stock.move._get_l10n_ro_move_line_vals_list``): core would count
        # them as bills of the order. Keep the vendor bills and refunds only.
        res = super()._compute_invoice()
        for order in self:
            invoices = order.invoice_ids.filtered(
                lambda move: move.is_purchase_document(include_receipts=True)
            )
            order.invoice_ids = invoices
            order.invoice_count = len(invoices)
        return res
