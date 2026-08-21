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
        string="Landed Cost Type",
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

    def _l10n_ro_create_svl_landed_cost(
        self,
        line,
        svl,
        cost_to_add,
        move_vals,
        valuation_layer_ids,
        cost_to_add_byproduct,
        product,
        svl_type="in",
    ):
        """Create the additional valuation layer (and accounting entry, if
        needed) for `svl`, then recurse on its tracked destination valuation
        layers (l10n_ro_svl_dest_ids) so the landed cost also reaches
        subsequent stock moves, e.g. a chain of internal transfers."""
        self.ensure_one()
        valuation_layer = self.l10n_ro_create_valuation_layer(
            line if svl_type == "in" else self.env["stock.valuation.adjustment.lines"],
            svl,
            cost_to_add,
        )
        valuation_layer_ids.append(valuation_layer.id)
        if product.cost_method == "average":
            cost_to_add_byproduct[product] += cost_to_add
        # Only a positive (held-inventory) svl retains a share of the
        # additional cost - a negative svl (internal-transfer mirror,
        # sale/consumption out layer, ...) always has remaining_qty == 0
        # and must stay at 0 remaining_value; it only forwards its cost
        # to its own tracked destinations below.
        if svl.quantity > 0:
            svl.remaining_value += cost_to_add
        if product.valuation == "real_time":
            if svl_type == "out":
                move_vals["date"] = svl.create_date
            svl_move_vals = move_vals
            amls = line._l10n_ro_prepare_accounting_entries(
                valuation_layer, svl_move_vals, cost_to_add, svl_type=svl_type
            )
            if amls:
                svl_move_vals["line_ids"] = amls
                svl_move = self.env["account.move"].create(svl_move_vals)
                valuation_layer.update({"account_move_id": svl_move.id})
                svl_move._post()

        for svl_out in svl.l10n_ro_svl_dest_ids.filtered(lambda s: s.quantity != 0):
            out_cost_to_add = (svl_out.quantity / svl.quantity) * cost_to_add
            if svl.quantity > 0:
                svl.remaining_value += out_cost_to_add
            self._l10n_ro_create_svl_landed_cost(
                line,
                svl_out,
                out_cost_to_add,
                move_vals,
                valuation_layer_ids,
                cost_to_add_byproduct,
                product,
                svl_type="out",
            )

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
            move_vals = {
                "journal_id": cost.account_journal_id.id,
                "date": cost.date,
                "ref": cost.name,
                "line_ids": [],
                "move_type": "entry",
            }
            valuation_layer_ids = []
            cost_to_add_byproduct = defaultdict(float)
            for line in cost.valuation_adjustment_lines.filtered(
                lambda line: line.move_id
            ):
                # Add distributed cost for each stock valuation layer.
                product = line.move_id.product_id
                for svl in line.move_id.stock_valuation_layer_ids.filtered(
                    lambda s: s.quantity != 0
                ):
                    if line.move_id._is_internal_transfer() and svl.quantity < 0:
                        # For internal transfers the negative svl is just the
                        # mirror of the positive one at destination (same
                        # move, linked via l10n_ro_svl_dest_ids); skip it so
                        # the landed cost isn't booked twice.
                        continue
                    cost_to_add = (
                        svl.quantity / line.move_id.quantity
                    ) * line.additional_landed_cost
                    # Creates the svl for this move and recurses on its
                    # tracked destinations (e.g. chained internal transfers)
                    # so the landed cost is distributed on all of them too.
                    cost._l10n_ro_create_svl_landed_cost(
                        line,
                        svl,
                        cost_to_add,
                        move_vals,
                        valuation_layer_ids,
                        cost_to_add_byproduct,
                        product,
                        svl_type="in",
                    )

                # Products with manual inventory valuation are ignored because
                # they do not need to create journal entries.
                if product.valuation != "real_time":
                    continue
            # batch standard price computation avoid recompute quantity_svl
            # at each iteration
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

    def reconcile_landed_cost(self):
        # Overwrite method to avoid reconciliation for Romania
        ro_landed_cost = self.filtered(lambda c: c.company_id.l10n_ro_accounting)
        res = super(StockLandedCost, self - ro_landed_cost).reconcile_landed_cost()
        return res


class AdjustmentLines(models.Model):
    _name = "stock.valuation.adjustment.lines"
    _inherit = ["stock.valuation.adjustment.lines", "l10n.ro.mixin"]

    def _l10n_ro_prepare_accounting_entries(
        self, valuation_layer, move_vals, cost_to_add, svl_type="in"
    ):
        """Prepare the account move lines (accounting entries) for
        each valuation layer."""
        self.ensure_one()
        cost_product = self.cost_line_id.product_id
        if not cost_product:
            return False

        acc_valuation = self.move_id._get_accounting_data_for_valuation()[3]
        accounts = self.product_id.product_tmpl_id.get_product_accounts()
        debit_account_id = acc_valuation
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

        # daca e acelasi cont sa nu mai faca nota
        if credit_account_id == debit_account_id:
            return []
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
