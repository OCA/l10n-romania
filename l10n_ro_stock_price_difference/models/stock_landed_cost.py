# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    l10n_ro_price_difference = fields.Boolean()

    def _get_targeted_move_ids(self):
        if not self._context.get("l10n_ro_price_difference_move_ids"):
            return super()._get_targeted_move_ids()
        return self._context["l10n_ro_price_difference_move_ids"]

    def create_valuation_layers(self, line, linked_layer, amount):
        if self.l10n_ro_price_difference:
            vals_list = []
            vals = self._prepare_landed_cost_vals(
                line, linked_layer, line.additional_landed_cost
            )
            vals_list.append(vals)
            if amount - line.additional_landed_cost != 0:
                vals_out = self._prepare_landed_cost_vals(
                    line,
                    linked_layer,
                    amount - line.additional_landed_cost,
                )
                vals_list.append(vals_out)
            valuation_layers = self.env["stock.valuation.layer"].create(vals_list)
            return valuation_layers
        return super().create_valuation_layers(line, linked_layer, amount)
