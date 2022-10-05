# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    l10n_ro_cost_type = fields.Selection(
        selection_add=[("price_diff", "Price Difference")],
        ondelete={"price_diff": "set default"},
    )

    def _get_targeted_move_ids(self):
        if not self._context.get("l10n_ro_price_difference_move_ids"):
            return super()._get_targeted_move_ids()

        return self._context["l10n_ro_price_difference_move_ids"]
