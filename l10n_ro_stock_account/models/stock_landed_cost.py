# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from collections import defaultdict

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero
from odoo.tools.safe_eval import safe_eval


class StockLandedCost(models.Model):
    _name = "stock.landed.cost"
    _inherit = ["stock.landed.cost", "l10n.ro.mixin"]

    l10n_ro_cost_type = fields.Selection(
        [("normal", "Normal")],
        default="normal",
        string="Romania - Landed Cost Type",
        states={"done": [("readonly", True)]},
    )

    def _prepare_landed_cost_svl_vals(self, linked_layer, amount):
        stock_move = linked_layer.stock_move_id
        product = linked_layer.stock_move_id.product_id

        return {
            "value": amount,
            "unit_cost": 0,
            "quantity": 0,
            "remaining_qty": 0,
            "stock_valuation_layer_id": linked_layer.id,
            "description": self.name,
            "stock_move_id": stock_move.id,
            "l10n_ro_stock_move_line_id": linked_layer.l10n_ro_stock_move_line_id.id,
            "product_id": product.id,
            "stock_landed_cost_id": self.id,
            "company_id": self.company_id.id,
        }

    def l10n_ro_create_valuation_layer(self, linked_layer, amount):
        vals = self._prepare_landed_cost_svl_vals(linked_layer, amount)
        valuation_layer = self.env["stock.valuation.layer"].create(vals)
        return valuation_layer

    def l10n_ro_get_move_vals(self, cost):
        move_vals = {
            "journal_id": cost.account_journal_id.id,
            "date": cost.date,
            "ref": cost.name,
            "line_ids": [],
            "move_type": "entry",
        }
        return move_vals

    def l10n_ro_create_account_move(self, line, svl, cost_to_add):
        move_obj = self.env["account.move"]
        move_vals = self.l10n_ro_get_move_vals(self)
        if svl.product_id.valuation == "real_time":
            move_vals.update(date=svl.create_date)
            svl_move_vals = move_vals
            amls = line._l10n_ro_prepare_accounting_entries(svl, cost_to_add)
            if amls:
                svl_move_vals["line_ids"] = amls
                svl_move = move_obj.create(svl_move_vals)
                svl.update({"account_move_id": svl_move.id})
                svl_move._post()

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

            cost_to_add_byproduct = defaultdict(lambda: 0.0)
            for line in cost.valuation_adjustment_lines.filtered(
                lambda line: line.move_id
            ):
                # Add distributed cost for each stock valuation layer.
                cost.l10n_ro_distribute_cost_propagate(
                    line,
                    line.move_id.stock_valuation_layer_ids,
                    cost_to_add_byproduct,
                    cost_to_add=line.additional_landed_cost,
                )
            # batch standard price computation avoid recompute quantity_svl at each iteration
            products = self.env["product.product"].browse(
                p.id for p in cost_to_add_byproduct.keys()
            )
            # iterate on recordset to prefetch efficiently quantity_svl
            for product in products:
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

    def l10n_ro_distribute_cost_propagate(
        self, line, svls, cost_to_add_byproduct, cost_to_add=0, propagate=False
    ):
        get_param = self.env["ir.config_parameter"].sudo().get_param
        stop = get_param(
            "l10n_ro_stock_account.stop_distribute_cost_propagate", "False"
        )
        stop = safe_eval(stop)
        if stop:
            return True

        for svl in svls.filtered(lambda s: s.quantity != 0):
            # Add distributed cost for each stock valuation layer.
            cost_to_add_byproduct, svl_cost_to_add = self.l10n_ro_distribute_cost(
                line, svl, cost_to_add_byproduct, cost_to_add, propagate
            )

            self.l10n_ro_propagate_cost(
                line, svl, cost_to_add_byproduct, svl_cost_to_add
            )
        return True

    def l10n_ro_distribute_cost(
        self, line, svl, cost_to_add_byproduct, cost_to_add, propagate=False
    ):
        product = svl.product_id
        svl_cost_to_add = (svl.quantity / svl.stock_move_id.quantity_done) * cost_to_add
        valuation_layer = self.l10n_ro_create_valuation_layer(svl, svl_cost_to_add)
        if svl.remaining_qty:
            svl.remaining_value += svl_cost_to_add
        if product.cost_method == "average" and not propagate:
            cost_to_add_byproduct[product] += svl_cost_to_add
        # Create separate account move for each svl
        if product.valuation == "real_time":
            self.l10n_ro_create_account_move(line, valuation_layer, svl_cost_to_add)
        return cost_to_add_byproduct, svl_cost_to_add

    def l10n_ro_propagate_cost(self, line, svl, cost_to_add_byproduct, cost_to_add):
        # Add separate svl for each quantity out
        for svl_out in svl.l10n_ro_svl_dest_ids.filtered(lambda s: s.quantity != 0):
            out_cost_to_add = (svl_out.quantity / svl.quantity) * cost_to_add
            valuation_layer_out = self.l10n_ro_create_valuation_layer(
                svl_out,
                out_cost_to_add,
            )
            if svl.remaining_qty:
                svl.remaining_value += out_cost_to_add
            # Create separate account move for each put svl
            if svl_out.quantity < 0:
                self.l10n_ro_create_account_move(
                    line, valuation_layer_out, out_cost_to_add
                )

            distributed_svls = svl_out.l10n_ro_svl_dest_ids.filtered(
                lambda s: s.quantity != 0
            )
            if distributed_svls:
                self.l10n_ro_propagate_cost(
                    line, svl_out, cost_to_add_byproduct, cost_to_add=out_cost_to_add
                )
        return True


class AdjustmentLines(models.Model):
    _name = "stock.valuation.adjustment.lines"
    _inherit = ["stock.valuation.adjustment.lines", "l10n.ro.mixin"]

    def _l10n_ro_get_debit_credit_account(self, valuation_layer, cost_to_add=0):
        def inverse_accounts(debit_account_id, credit_account_id):
            return credit_account_id, debit_account_id

        self.ensure_one()
        cost_product = self.cost_line_id.product_id
        src_location = valuation_layer.stock_move_id.location_id
        dest_location = valuation_layer.stock_move_id.location_dest_id
        accounts = self.product_id.product_tmpl_id.get_product_accounts()

        debit_account_id = credit_account_id = (
            accounts.get("stock_valuation") and accounts["stock_valuation"].id or False
        )
        if dest_location.l10n_ro_property_stock_valuation_account_id:
            debit_account_id = (
                dest_location.l10n_ro_property_stock_valuation_account_id.id
            )
        if src_location.l10n_ro_property_stock_valuation_account_id:
            credit_account_id = (
                src_location.l10n_ro_property_stock_valuation_account_id.id
            )

        # If the stock move is dropshipped move we need to get the cost account
        # instead the stock valuation account
        if valuation_layer.stock_move_id._is_dropshipped():
            debit_account_id = (
                accounts.get("expense") and accounts["expense"].id or False
            )
        if valuation_layer.stock_move_id._is_in():
            credit_account_id = (
                self.cost_line_id.account_id.id
                or cost_product.categ_id.property_stock_account_input_categ_id.id
            )
        if valuation_layer.stock_move_id._is_out():
            debit_account_id = (
                accounts.get("expense") and accounts["expense"].id or False
            )
            if src_location.l10n_ro_property_account_expense_location_id:
                debit_account_id = (
                    src_location.l10n_ro_property_account_expense_location_id.id
                )
        if "return" in valuation_layer.l10n_ro_valued_type:
            debit_account_id, credit_account_id = inverse_accounts(
                debit_account_id, credit_account_id
            )
        if valuation_layer.stock_move_id._is_in() and cost_to_add < 0:
            debit_account_id, credit_account_id = inverse_accounts(
                debit_account_id, credit_account_id
            )
        if valuation_layer.stock_move_id._is_out() and cost_to_add > 0:
            debit_account_id, credit_account_id = inverse_accounts(
                debit_account_id, credit_account_id
            )
        return debit_account_id, credit_account_id

    def _l10n_ro_prepare_accounting_entries(self, valuation_layer, cost_to_add):
        """Prepare the account move lines (accounting entries) for each valuation layer."""
        self.ensure_one()
        cost_product = self.cost_line_id.product_id
        if not cost_product:
            return False

        AccountMoveLine = []
        base_line = {
            "name": self.name,
            "product_id": self.product_id.id,
            "quantity": 0,
        }
        debit_account_id, credit_account_id = self._l10n_ro_get_debit_credit_account(
            valuation_layer, cost_to_add
        )
        if debit_account_id == credit_account_id:
            return False

        if valuation_layer.stock_move_id._is_internal_transfer():
            base_line["name"] += ": " + _(" internal transfer")
        elif valuation_layer.quantity < 0:
            base_line["name"] += ": " + _(" already out")
        debit_line = dict(base_line, account_id=debit_account_id)
        credit_line = dict(base_line, account_id=credit_account_id)
        debit_line["debit"] = abs(cost_to_add)
        credit_line["credit"] = abs(cost_to_add)
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
