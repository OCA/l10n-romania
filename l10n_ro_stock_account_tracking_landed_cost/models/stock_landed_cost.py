# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models


class StockLandedCost(models.Model):
    _name = "stock.landed.cost"
    _inherit = ["stock.landed.cost", "l10n.ro.mixin"]

    def _prepare_landed_cost_svl_vals(self, line, linked_layer, amount):
        vals = super()._prepare_landed_cost_svl_vals(line, linked_layer, amount)
        sml = linked_layer.l10n_ro_stock_move_line_id.id
        vals.update(
            {
                "l10n_ro_stock_move_line_id": sml,
            }
        )
        return vals

    def _button_validate_adjust_quantity_out_costs(
        self, svl, cost_line, cost_to_add, svl_move_vals, cost_to_add_byproduct
    ):
        for svl_out in svl.l10n_ro_svl_dest_ids.filtered(lambda s: s.quantity != 0):
            move = self.env["account.move"]
            product = svl.product_id
            out_cost_to_add = (svl_out.quantity / svl.quantity) * cost_to_add
            valuation_layer_out = cost_line.cost_id.l10n_ro_create_valuation_layer(
                self.env["stock.valuation.adjustment.lines"],
                svl_out,
                out_cost_to_add,
            )
            svl.remaining_value += out_cost_to_add

            if product.cost_method == "average":
                cost_to_add_byproduct[product] += out_cost_to_add
            # Create separate account move for each put svl
            if product.valuation == "real_time":
                svl_move_vals.update(date=svl_out.create_date)
                amls = cost_line._l10n_ro_prepare_accounting_entries(
                    valuation_layer_out,
                    svl_move_vals,
                    out_cost_to_add,
                    svl_type="out",
                )
                if amls:
                    svl_move_vals["line_ids"] = amls
                    svl_move = move.create(svl_move_vals)
                    valuation_layer_out.update({"account_move_id": svl_move.id})
                    svl_move._post()
