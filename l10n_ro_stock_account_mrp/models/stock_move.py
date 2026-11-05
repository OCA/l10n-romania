# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_kit_value_per_unit(self):
        """``sale_mrp`` returns the price of one kit unit for a component move
        linked to the sale line of a kit: right for the COGS of the kit, wrong
        as the cost of the component (a customer return of a kit as last
        incoming move set the cost of the component to the price of a whole
        kit). Fall back to the unit value of the move in that case."""
        if self.env.context.get("l10n_ro_no_kit_price_unit"):
            return 0
        return super()._get_kit_value_per_unit()
