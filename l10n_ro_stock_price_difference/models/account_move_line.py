# Copyright (C) 2025 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models
from odoo.tools.float_utils import float_is_zero

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    def l10n_ro_get_stock_valuation_difference(self):
        """
        Se obtine diferenta dintre valoarea stocului si valoarea din factura.
        Returneaza un dictionar cu cheile:
            - value_diff: diferenta valorica
            - qty_diff: diferenta cantitativa
            - stock_move: ultima miscare de stoc asociata
        """
        line = self
        res = {
            "value_diff": 0.0,
            "qty_diff": 0.0,
            "stock_move_id": self.env["stock.move"],
        }

        # Retrieve stock valuation moves.
        if not line.purchase_line_id:
            return res

        if line.purchase_line_id.product_id.purchase_method != "receive":
            return res

        if not line._eligible_for_stock_account():
            return res

        if line.product_id.cost_method == "standard":
            return res

        if line.product_id.cost_method == "average":
            return res

        stock_moves = self._get_stock_moves().filtered(lambda sm: sm.state == "done")
        if not stock_moves:
            return res

        # Reception on notice: account 408 is the pivot, so the price difference is
        # what is left on it once the exchange rate difference is recognised (see
        # l10n_ro_stock_account). Comparing the invoice value with the stock value
        # here would take the rate delta for a price difference and capitalise it
        # into inventory, on top of the 765/665 entry - the same delta twice.
        notice_price_diff, notice_rate_diff = self._l10n_ro_notice_settlement_amounts()
        if not float_is_zero(
            notice_rate_diff, precision_rounding=self.company_id.currency_id.rounding
        ) or not float_is_zero(
            notice_price_diff, precision_rounding=self.company_id.currency_id.rounding
        ):
            res["stock_move_id"] = stock_moves.sorted("id", reverse=True)[:1].id
            res["value_diff"] = notice_price_diff
            return res

        stock_value = stock_qty = 0.0
        for stock_move in stock_moves:
            if stock_move._is_incoming():
                stock_value += stock_move.value
                stock_qty += stock_move.quantity
            else:
                stock_value -= stock_move.value
                stock_qty -= stock_move.quantity
        res["stock_move_id"] = stock_moves.sorted("id", reverse=True)[:1].id
        precision = line.product_uom_id.rounding or line.product_id.uom_id.rounding

        if float_is_zero(stock_qty, precision_rounding=precision):
            return res

        inv_lines = self.search(
            [
                ("purchase_line_id", "=", line.purchase_line_id.id),
                ("move_id.state", "!=", "cancel"),
            ]
        )
        inv_value = inv_qty = 0
        for line in inv_lines:
            line_qty = line.product_uom_id._compute_quantity(
                line.quantity, line.product_id.uom_id
            )
            inv_qty += (-1 if line.move_id.move_type == "in_refund" else 1) * line_qty

        if inv_qty != 0 and inv_qty != stock_qty:
            # In case of partial invoicing, we compute the unit price based on
            # the invoiced quantity.
            inv_value = sum(inv_lines.mapped("balance")) / inv_qty * stock_qty
        else:
            inv_value = sum(inv_lines.mapped("balance"))
        currency = line.currency_id or self.env.company.currency_id
        res.update(
            {
                "value_diff": currency.round(inv_value - stock_value),
                "qty_diff": inv_qty - stock_qty,
            }
        )
        return res

    def l10n_ro_modify_stock_value(self, diff_dict=None):
        self.ensure_one()
        if not diff_dict:
            return
        self = self.with_company(self.company_id)
        val_dif = diff_dict.get("value_diff", 0.0)
        if float_is_zero(val_dif, precision_rounding=0.01):
            return

        # If this stock move's price difference was already corrected by a
        # prior confirm (e.g. the bill was reset to draft and confirmed
        # again), skip it: the correction was already applied and redoing it
        # would double it up, since the diff is recomputed from the original
        # move's value, which distribution to destinations does not update.
        stock_move_id = diff_dict.get("stock_move_id")
        if stock_move_id and self.env["stock.landed.cost"].search_count(
            [
                ("l10n_ro_cost_type", "=", "price_diff"),
                ("state", "=", "done"),
                ("valuation_adjustment_lines.move_id", "=", stock_move_id),
            ]
        ):
            return

        # Distribute in case having stock move destinations or account in the
        # invoice line is different than the product stock account
        stock_moves = self._get_stock_moves().filtered(lambda sm: sm.state == "done")
        product_account = self.product_id.product_tmpl_id.with_context(
            l10_ro_stock_move=stock_moves[0]
        )._get_product_accounts()["stock_valuation"]
        if (
            not stock_moves.mapped("l10n_ro_move_track_dest_ids")
            and self.account_id == product_account
        ):
            return
        price_diff_lc = self._l10n_ro_create_price_difference_landed_cost(val_dif)
        price_diff_lc.compute_landed_cost()
        price_diff_lc.with_context(
            l10n_ro_price_difference_move_ids=diff_dict.get("stock_move_id")
        ).button_validate()

    def _l10n_ro_create_price_difference_landed_cost(self, value):
        vals = self.l10n_ro_prepare_price_difference_landed_cost(value)
        return self.env["stock.landed.cost"].sudo().create(vals)

    def l10n_ro_prepare_price_difference_landed_cost(self, value):
        price_diff_product = self._l10n_ro_get_or_create_price_difference_product()
        stock_journal_id = (
            self.company_id.account_stock_journal_id
            or self.company_id.lc_journal_id
            or False
        )
        return dict(
            account_journal_id=stock_journal_id and stock_journal_id.id,
            l10n_ro_cost_type="price_diff",
            l10n_ro_only_on_distributed_lines=True,
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

    def _l10n_ro_get_or_create_price_difference_product(self):
        price_diff_product = (
            self.company_id.l10n_ro_property_stock_price_difference_product_id
        )
        if not price_diff_product:
            serv_acc = self.env["account.account"].search(
                [
                    ("account_type", "=", "expense"),
                    ("company_ids", "in", [self.company_id.id]),
                ],
                limit=1,
            )

            price_diff_product = self.env["product.product"].create(
                {
                    "name": "Price Difference Between Reception and Bill",
                    "categ_id": self.env.ref("product.product_category_services").id,
                    "type": "service",
                    "landed_cost_ok": True,
                    "property_account_expense_id": serv_acc.id if serv_acc else False,
                }
            )

            company = self.sudo().company_id
            company.l10n_ro_property_stock_price_difference_product_id = (
                price_diff_product
            )

        return price_diff_product
