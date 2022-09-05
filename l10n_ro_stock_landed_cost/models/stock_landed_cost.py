from odoo import _, api, models
from odoo.exceptions import UserError


class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    def button_draft(self):
        self.ensure_one()
        if self.company_id.l10n_ro_accounting and self.state == "done":
            self.account_move_id.button_draft()
            self.write({"state": "draft"})

    def button_validate(self):
        for rec in self:
            if rec.company_id.l10n_ro_accounting:
                if rec.account_move_id:
                    raise UserError(
                        _(
                            f"For Landed Cost = ({rec.id}, {rec.name}), you already have a Journal Entry. You can NOT revalidate. Create another Landed Cost (the reason is that you'll have old svl with this landed cost) "
                        )
                    )
                # we must rise error if the stock moves svl have remaining_qty 0
                # this can be a serious problem at dvi, but also at landed cost
                # because it will not create all svl's that is supposed to
                move_lines = rec.picking_ids.move_lines
                if not move_lines:
                    raise UserError(
                        _(
                            f"For landed cost=({rec.id},{rec.name}) you do not have stock_move_lines to distribute the cost"
                        )
                    )
                svl_without_remaining_qty = (
                    move_lines.stock_valuation_layer_ids.filtered(
                        lambda r: not r.remaining_qty
                    )
                )
                if svl_without_remaining_qty:
                    raise UserError(
                        _(
                            f"For landed cost=({rec.id},{rec.name}) you do not svl_without_remaining_qty={svl_without_remaining_qty}"
                        )
                    )
        return super().button_validate()
