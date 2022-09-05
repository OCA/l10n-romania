# Copyright (C) 2022 cbssolutions.ro
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = "stock.picking"

    def _action_done(self):
        # for the case is valued reception must take prices form invoice
        # if is a reception form po, we will create invoice for this picking
        res = super()._action_done()
        if (
            len(self) == 1
            and self.is_l10n_ro_record
            and hasattr(self, "purchase_id")
            and self.purchase_id  # is installed puchase_stock
            and self.move_lines.filtered(
                lambda r: r.quantity_done and r.product_id.valuation == "real_time"
            )
            # is not a notice - does not have journal entry for svl:
            and not self.move_lines.stock_valuation_layer_ids.filtered(
                lambda r: r.account_move_id
            )
        ):
            self.purchase_id.with_context(
                inv_for_reception_picking=self.id
            ).action_create_invoice()
        return res
