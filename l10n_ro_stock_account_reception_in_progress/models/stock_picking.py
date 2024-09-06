# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "l10n.ro.mixin"]

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
        return res
