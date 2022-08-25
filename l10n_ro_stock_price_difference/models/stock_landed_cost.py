# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from collections import defaultdict

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    def _get_targeted_move_ids(self):
        if not self._context.get("l10n_ro_price_difference_move_ids"):
            return super()._get_targeted_move_ids()

        return self._context["l10n_ro_price_difference_move_ids"]

    def create_valuation_layer(self, line, linked_layer, amount):
        valuation_layer = self.env["stock.valuation.layer"].create(
            {
                "value": amount,
                "unit_cost": 0,
                "quantity": 0,
                "remaining_qty": 0,
                "stock_valuation_layer_id": linked_layer.id,
                "description": self.name,
                "stock_move_id": line.move_id.id,
                "product_id": line.move_id.product_id.id,
                "stock_landed_cost_id": self.id,
                "company_id": self.company_id.id,
            }
        )
        return valuation_layer

    def button_validate(self):
        if not self.company_id.romanian_accounting:
            return super().button_validate()
        self._check_can_validate()
        cost_without_adjusment_lines = self.filtered(
            lambda c: not c.valuation_adjustment_lines
        )
        if cost_without_adjusment_lines:
            cost_without_adjusment_lines.compute_landed_cost()
        if not self._check_sum():
            raise UserError(
                _(
                    "Cost and adjustments lines do not match. "
                    "You should maybe recompute the landed costs."
                )
            )

        for cost in self:
            cost = cost.with_company(cost.company_id)
            move = self.env["account.move"]
            move_vals = {
                "journal_id": cost.account_journal_id.id,
                "date": cost.date,
                "ref": cost.name,
                "line_ids": [],
                "move_type": "entry",
            }
            valuation_layer_ids = []
            cost_to_add_byproduct = defaultdict(lambda: 0.0)
            for line in cost.valuation_adjustment_lines.filtered(
                lambda line: line.move_id
            ):
                remaining_qty = sum(
                    line.move_id.stock_valuation_layer_ids.mapped("remaining_qty")
                )
                linked_layer = line.move_id.stock_valuation_layer_ids[:1]

                # Prorate the value at what's still in stock
                cost_to_add = (
                    remaining_qty / line.move_id.product_qty
                ) * line.additional_landed_cost

                # Romania change to create separate valuation layer for price difference
                # and for the quantity out difference
                if not cost.company_id.currency_id.is_zero(cost_to_add):
                    valuation_layer = cost.create_valuation_layer(
                        line, linked_layer, line.additional_landed_cost
                    )
                    linked_layer.remaining_value += cost_to_add
                    valuation_layer_ids.append(valuation_layer.id)
                    if cost_to_add - line.additional_landed_cost != 0:
                        valuation_layer_out = cost.create_valuation_layer(
                            line,
                            linked_layer,
                            cost_to_add - line.additional_landed_cost,
                        )
                        valuation_layer_ids.append(valuation_layer_out.id)
                # End Romania change

                # Update the AVCO
                product = line.move_id.product_id
                if product.cost_method == "average":
                    cost_to_add_byproduct[product] += cost_to_add
                # Products with manual inventory valuation are ignored because
                # they do not need to create journal entries.
                if product.valuation != "real_time":
                    continue
                # `remaining_qty` is negative if the move is out and delivered
                # proudcts that were not
                # in stock.
                qty_out = 0
                if line.move_id._is_in():
                    qty_out = line.move_id.product_qty - remaining_qty
                elif line.move_id._is_out():
                    qty_out = line.move_id.product_qty
                move_vals["line_ids"] += line._create_accounting_entries(move, qty_out)

            # batch standard price computation avoid recompute quantity_svl at each iteration
            products = self.env["product.product"].browse(
                p.id for p in cost_to_add_byproduct.keys()
            )
            for (
                product
            ) in products:  # iterate on recordset to prefetch efficiently quantity_svl
                if not float_is_zero(
                    product.quantity_svl, precision_rounding=product.uom_id.rounding
                ):
                    product.with_company(cost.company_id).sudo().with_context(
                        disable_auto_svl=True
                    ).standard_price += (
                        cost_to_add_byproduct[product] / product.quantity_svl
                    )

            # move_vals['stock_valuation_layer_ids'] = [(6, None, valuation_layer_ids)]
            # We will only create the accounting entry when there are defined lines
            # (the lines will be those linked to products of real_time valuation category).
            cost_vals = {"state": "done"}
            if move_vals.get("line_ids"):
                move = move.create(move_vals)
                cost_vals.update({"account_move_id": move.id})
            cost.write(cost_vals)
            if cost.account_move_id:
                move._post()

            if (
                cost.vendor_bill_id
                and cost.vendor_bill_id.state == "posted"
                and cost.company_id.anglo_saxon_accounting
            ):
                all_amls = cost.vendor_bill_id.line_ids | cost.account_move_id.line_ids
                for product in cost.cost_lines.product_id:
                    accounts = product.product_tmpl_id.get_product_accounts()
                    input_account = accounts["stock_input"]
                    all_amls.filtered(
                        lambda aml: aml.account_id == input_account
                        and not aml.reconciled
                    ).reconcile()

        return True


class AdjustmentLines(models.Model):
    _inherit = "stock.valuation.adjustment.lines"

    def _create_account_move_line(
        self, move, credit_account_id, debit_account_id, qty_out, already_out_account_id
    ):
        res = super()._create_account_move_line(
            move, credit_account_id, debit_account_id, qty_out, already_out_account_id
        )
        if self.cost_id.company_id.romanian_accounting:
            # Remove account move lines generated for the same account
            if credit_account_id == debit_account_id:
                res = res[2:]
            if qty_out > 0:
                if (
                    credit_account_id == already_out_account_id
                    and self.additional_landed_cost > 0
                ):
                    res = res[2:]
                if (
                    debit_account_id == already_out_account_id
                    and self.additional_landed_cost < 0
                ):
                    if credit_account_id == debit_account_id:
                        res = res[2:]
                    elif len(res) > 4:
                        res = res[0:2] + res[4:]
        return res
