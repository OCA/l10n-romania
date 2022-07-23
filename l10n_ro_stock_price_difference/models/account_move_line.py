# Copyright (C) 2022 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models
from odoo.tools.float_utils import float_is_zero

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def get_stock_valuation_difference(self):
        """Se obtine diferenta dintre evaloarea stocului si valoarea din factura"""
        line = self

        # Retrieve stock valuation moves.
        if not line.purchase_line_id:
            return 0.0

        if line.purchase_line_id.product_id.purchase_method != "receive":
            return 0.0

        valuation_stock_moves = self._get_valuation_stock_moves()

        if not valuation_stock_moves:
            return 0.0

        valuation_total = 0
        valuation_total_qty = 0
        for val_stock_move in valuation_stock_moves:
            svl = (
                val_stock_move.sudo()
                .mapped("stock_valuation_layer_ids")
                .filtered(lambda l: l.quantity)
            )
            layers_qty = sum(svl.mapped("quantity"))
            layers_values = sum(svl.mapped("value"))

            valuation_total += layers_values
            valuation_total_qty += layers_qty

        precision = line.product_uom_id.rounding or line.product_id.uom_id.rounding
        if float_is_zero(valuation_total_qty, precision_rounding=precision):
            return 0.0

        lines = self.search(
            [
                ("purchase_line_id", "=", line.purchase_line_id.id),
                ("move_id.state", "!=", "cancel"),
            ]
        )
        inv_qty = 0
        for line in lines:
            inv_qty += (
                -1 if line.move_id.move_type == "in_refund" else 1
            ) * line.quantity
        accc_balance = sum(lines.mapped("balance")) / inv_qty * valuation_total_qty
        diff = abs(accc_balance) - valuation_total
        qty_diff = inv_qty - valuation_total_qty
        return diff, qty_diff

    def modify_stock_valuation(self, price_val_dif):
        # se adauga la evaluarea miscarii de stoc
        if not self.purchase_line_id:
            return 0.0
        valuation_stock_move = self.env["stock.move"].search(
            [
                ("purchase_line_id", "=", self.purchase_line_id.id),
                ("state", "=", "done"),
                ("product_qty", "!=", 0.0),
            ],
            order="id desc",
            limit=1,
        )
        value = price_val_dif
        # trebuie cantitate din factura in unitatea produsului si apoi
        value = self.product_uom_id._compute_price(value, self.product_id.uom_id)

        lc = self._create_price_difference_landed_cost(value)
        lc.compute_landed_cost()
        lc.with_context(
            l10n_ro_price_difference_move_ids=valuation_stock_move
        ).button_validate()

        lc.stock_valuation_layer_ids.mapped("account_move_id")

        # svl-ul creat trebuie sa aiba quantity diferit de 0,
        # pentru a fi inclus data viitoare in get_stock_valuation_difference
        lc.stock_valuation_layer_ids.filtered(
            lambda svl: svl.value == lc.amount_total
        ).write(
            {
                "quantity": 1e-50,
                "description": "Price Difference",
                "stock_landed_cost_id": None,
            }
        )

    def prepare_price_difference_landed_cost(self, value):
        price_diff_product = self._get_or_create_price_difference_product()
        stock_journal_id = self.product_id.categ_id.property_stock_journal or False
        return dict(
            account_journal_id=stock_journal_id and stock_journal_id.id,
            cost_lines=[
                (
                    0,
                    0,
                    {
                        "name": "Price Difference: equal split",
                        "split_method": "by_quantity",
                        "price_unit": value,
                        "product_id": price_diff_product.id,
                        "account_id": self.account_id.id,
                    },
                )
            ],
        )

    def _create_price_difference_landed_cost(self, value):
        vals = self.prepare_price_difference_landed_cost(value)
        return self.env["stock.landed.cost"].create(vals)

    def _get_or_create_price_difference_product(self):
        price_diff_product = self.company_id.property_stock_price_difference_product_id
        if not price_diff_product:
            serv_acc = self.env["account.account"].search(
                [
                    ("user_type_id.name", "=", "Expense"),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )

            price_diff_product = self.env["product.product"].create(
                {
                    "name": "Price Difference Between Reception and Bill",
                    "categ_id": self.env.ref("product.product_category_all").id,
                    "type": "service",
                    "landed_cost_ok": True,
                    "property_account_expense_id": serv_acc if serv_acc else False,
                }
            )

            self.company_id.property_stock_price_difference_product_id = (
                price_diff_product
            )

        return price_diff_product
