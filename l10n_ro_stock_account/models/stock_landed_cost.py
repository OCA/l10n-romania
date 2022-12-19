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

    def l10n_ro_create_diff_valuation_layer(self, line, linked_layer, amount):
        """
        Aici sunt in cazul in care s-au facut deja niste livrari inainte
        sa se inregistreze landed cost.

        Va trebui ca noul landed cost cu valoarea <amount> sa fie legat
        de svl-ul de iesire (de obicei acesta o sa aiba
        valued_type = delivery). Daca sunt mai multe svl-uri, atunci
        trebuie sa se distribuie <amount> proportional pt fiecare svl out

        Totodata nu trebuie luate in calcul retururile la furnizor
        (care sunt tot out-uri)
        """
        valuation_layer_ids = []
        out_svls = linked_layer.l10n_ro_svl_dest_ids.filtered(
            lambda svl: "_return" not in svl.l10n_ro_valued_type
        )
        if out_svls:
            qty_out_total = abs(sum(out_svls.mapped("quantity")))
            if qty_out_total > 0:
                for out_svl in out_svls:
                    amount_ratio = abs(out_svl.quantity / qty_out_total)
                    am = amount_ratio * amount
                    valuation_layer_out = self.l10n_ro_create_valuation_layer(
                        None,
                        out_svl,
                        am,
                    )
                    valuation_layer_ids.append(valuation_layer_out.id)

        else:
            valuation_layer_out = self.l10n_ro_create_valuation_layer(
                line,
                linked_layer,
                amount,
            )
            valuation_layer_ids.append(valuation_layer_out.id)
        return valuation_layer_ids

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
                valuation_layer = cost.l10n_ro_create_valuation_layer(
                    line, linked_layer, line.additional_landed_cost
                )
                linked_layer.remaining_value += cost_to_add
                valuation_layer_ids.append(valuation_layer.id)
                if cost_to_add - line.additional_landed_cost != 0:
                    valuation_layer_out = cost.l10n_ro_create_diff_valuation_layer(
                        line,
                        linked_layer,
                        cost_to_add - line.additional_landed_cost,
                    )
                    valuation_layer_ids += valuation_layer_out

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
                # products that were not in stock.

                # Romania change: extract method to generate accounting entries
                # for quantity already delivered.
                move_vals = line._prepare_out_accounting_entries(
                    move_vals, move, remaining_qty
                )
                # Romania end change

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
    _name = "stock.valuation.adjustment.lines"
    _inherit = ["stock.valuation.adjustment.lines", "l10n.ro.mixin"]

    def _prepare_out_accounting_entries(self, move_vals, move, remaining_qty):
        qty_out = 0
        if self.move_id._is_in():
            qty_out = self.move_id.product_qty - remaining_qty
        elif self.move_id._is_out():
            qty_out = self.move_id.product_qty
        move_vals["line_ids"] += self._create_accounting_entries(move, qty_out)
        return move_vals

    def _create_account_move_line(
        self, move, credit_account_id, debit_account_id, qty_out, already_out_account_id
    ):
        res = super()._create_account_move_line(
            move, credit_account_id, debit_account_id, qty_out, already_out_account_id
        )
        if self.is_l10n_ro_record:
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
