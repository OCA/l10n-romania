from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    l10n_ro_second_account_id = fields.Many2one(
        "account.account",
        compute="_compute_second_account",
        store=True,
        string="Valuation Account",
    )

    @api.depends("product_id", "account_move_id", "location_id", "location_dest_id")
    def _compute_second_account(self):
        for move in self:
            loc_dest = move.location_dest_id
            loc_src = move.location_id

            if loc_dest.usage == "internal" and loc_src.usage == "internal":
                move.l10n_ro_second_account_id = (
                    loc_src.l10n_ro_property_stock_valuation_account_id
                )
            else:
                move.l10n_ro_second_account_id = False
