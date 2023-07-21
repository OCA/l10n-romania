# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from collections import defaultdict

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


class StockLandedCost(models.Model):
    _name = "stock.landed.cost"
    _inherit = ["stock.landed.cost", "l10n.ro.mixin"]

    l10n_ro_cost_type = fields.Selection(
        [("normal", "Normal")],
        default="normal",
        string="Romania - Landed Cost Type",
        states={"done": [("readonly", True)]},
    )

    def _prepare_landed_cost_svl_vals(self, line, linked_layer, amount):
        if line:
            stock_move_id = line.move_id
            product_id = line.move_id.product_id
        else:
            stock_move_id = linked_layer.stock_move_id
            product_id = linked_layer.stock_move_id.product_id

        return {
            "value": amount,
            "unit_cost": 0,
            "quantity": 0,
            "remaining_qty": 0,
            "stock_valuation_layer_id": linked_layer.id,
            "description": self.name,
            "stock_move_id": stock_move_id.id,
            "l10n_ro_stock_move_line_id": linked_layer.l10n_ro_stock_move_line_id.id,
            "product_id": product_id.id,
            "stock_landed_cost_id": self.id,
            "company_id": self.company_id.id,
        }

    def l10n_ro_create_valuation_layer(self, line, linked_layer, amount):
        vals = self._prepare_landed_cost_svl_vals(line, linked_layer, amount)
        valuation_layer = self.env["stock.valuation.layer"].create(vals)
        return valuation_layer

    def button_validate(self):
        # Overwrite method for Romania to extract stock valuation layer
        # creation in a separate method
        if not self.filtered(lambda c: c.company_id.l10n_ro_accounting):
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
                # Add distributed cost for each stock valuation layer.
                product = line.move_id.product_id
                for svl in line.move_id.stock_valuation_layer_ids.filtered(
                    lambda s: s.quantity != 0
                ):
                    cost_to_add = (
                        svl.quantity / line.move_id.quantity_done
                    ) * line.additional_landed_cost
                    valuation_layer = cost.l10n_ro_create_valuation_layer(
                        line, svl, cost_to_add
                    )
                    svl.remaining_value += cost_to_add
                    valuation_layer_ids.append(valuation_layer.id)
                    if product.cost_method == "average":
                        cost_to_add_byproduct[product] += cost_to_add
                    # Create separate account move for each svl
                    if product.valuation == "real_time":
                        svl_move_vals = move_vals
                        amls = line._l10n_ro_prepare_accounting_entries(
                            valuation_layer, svl_move_vals, cost_to_add, svl_type="in"
                        )
                        if amls:
                            svl_move_vals["line_ids"] = amls
                            svl_move = move.create(svl_move_vals)
                            valuation_layer.update({"account_move_id": svl_move.id})
                            svl_move._post()

                    # Add separate svl for each quantity out
                    for svl_out in svl.l10n_ro_svl_dest_ids.filtered(
                        lambda s: s.quantity != 0
                    ):
                        out_cost_to_add = (
                            svl_out.quantity / svl.quantity
                        ) * cost_to_add
                        valuation_layer_out = cost.l10n_ro_create_valuation_layer(
                            self.env["stock.valuation.adjustment.lines"],
                            svl_out,
                            out_cost_to_add,
                        )
                        svl.remaining_value += out_cost_to_add
                        valuation_layer_ids.append(valuation_layer_out.id)

                        if product.cost_method == "average":
                            cost_to_add_byproduct[product] += out_cost_to_add
                        # Create separate account move for each put svl
                        if product.valuation == "real_time":
                            svl_move_vals = move_vals
                            amls = line._l10n_ro_prepare_accounting_entries(
                                valuation_layer_out,
                                svl_move_vals,
                                out_cost_to_add,
                                svl_type="out",
                            )
                            if amls:
                                svl_move_vals["line_ids"] = amls
                                svl_move = move.create(svl_move_vals)
                                valuation_layer_out.update(
                                    {"account_move_id": svl_move.id}
                                )
                                svl_move._post()

                # Products with manual inventory valuation are ignored because
                # they do not need to create journal entries.
                if product.valuation != "real_time":
                    continue
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

            cost_vals = {"state": "done"}
            cost.write(cost_vals)
        return True


class AdjustmentLines(models.Model):
    _name = "stock.valuation.adjustment.lines"
    _inherit = ["stock.valuation.adjustment.lines", "l10n.ro.mixin"]

    def _l10n_ro_prepare_accounting_entries(
        self, valuation_layer, move_vals, cost_to_add, svl_type="in"
    ):
        """Prepare the account move lines (accounting entries) for each valuation layer."""
        self.ensure_one()
        cost_product = self.cost_line_id.product_id
        if not cost_product:
            return False
        accounts = self.product_id.product_tmpl_id.get_product_accounts()
        debit_account_id = (
            accounts.get("stock_valuation") and accounts["stock_valuation"].id or False
        )
        credit_account_id = (
            self.cost_line_id.account_id.id
            or cost_product.categ_id.property_stock_account_input_categ_id.id
        )

        # If the stock move is dropshipped move we need to get the cost account
        # instead the stock valuation account
        if self.move_id._is_dropshipped():
            debit_account_id = (
                accounts.get("expense") and accounts["expense"].id or False
            )
        already_out_account_id = accounts["stock_output"].id
        if (
            debit_account_id == credit_account_id
            and credit_account_id == already_out_account_id
        ):
            return False

        if not credit_account_id:
            raise UserError(
                _("Please configure Stock Expense Account for product: %s.")
                % (cost_product.name)
            )
        AccountMoveLine = []

        base_line = {
            "name": self.name,
            "product_id": self.product_id.id,
            "quantity": 0,
        }

        if svl_type == "out":
            credit_account_id = self.product_id.product_tmpl_id.get_product_accounts()[
                "expense"
            ].id
            debit_account_id = already_out_account_id
            base_line["name"] += ": " + _(" already out")
        debit_line = dict(base_line, account_id=debit_account_id)
        credit_line = dict(base_line, account_id=credit_account_id)
        if cost_to_add > 0:
            debit_line["debit"] = cost_to_add
            credit_line["credit"] = cost_to_add
        else:
            # negative cost, reverse the entry
            debit_line["credit"] = -cost_to_add
            credit_line["debit"] = -cost_to_add
        AccountMoveLine.append([0, 0, debit_line])
        AccountMoveLine.append([0, 0, credit_line])

        return AccountMoveLine

    def _create_account_move_line(
        self, move, credit_account_id, debit_account_id, qty_out, already_out_account_id
    ):
        res = super()._create_account_move_line(
            move, credit_account_id, debit_account_id, qty_out, already_out_account_id
        )
        if self.is_l10n_ro_record:
            return self.env["account.move.line"]
        return res
