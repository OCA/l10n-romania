# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "l10n.ro.mixin"]

    def l10n_ro_set_valuations_invoice_line(self, invoices):
        for invoice in invoices:
            invoice_lines = invoice.invoice_line_ids.filtered(
                lambda l: not l.display_type
            )
            for line in invoice_lines:
                valuation_stock_moves = line._l10n_ro_get_valuation_stock_moves()
                if valuation_stock_moves:
                    svls = valuation_stock_moves.sudo().mapped(
                        "stock_valuation_layer_ids"
                    )
                    svls = svls.filtered(lambda l: not l.l10n_ro_invoice_line_id)
                    svls.write(
                        {
                            "l10n_ro_invoice_line_id": line.id,
                            "l10n_ro_invoice_id": line.move_id.id,
                        }
                    )

    def _action_done(self):
        res = super()._action_done()
        l10n_ro_records = self.filtered("is_l10n_ro_record")
        for picking in l10n_ro_records:
            if picking.purchase_id.l10n_ro_reception_in_progress:
                invoices = picking.purchase_id.invoice_ids
                if len(invoices) > 1:
                    raise ValidationError(
                        _(
                            "You cannot have 2 invoices on one purchase order "
                            "marked as Reception in Progress."
                        )
                    )
                if invoices:
                    invoices.l10n_ro_fix_price_difference_svl()
                    self.l10n_ro_set_valuations_invoice_line(invoices)
        return res
