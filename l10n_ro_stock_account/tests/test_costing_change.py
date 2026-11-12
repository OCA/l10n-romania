# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockCostingChange(TestStockCommon):
    """Changing the costing method must not post an entry from the stock
    account to itself: in Romania input, output and valuation accounts are the
    same, so the standard entry is always balanced on a single account."""

    def _stock_journal_entries(self, product):
        return self.env["account.move.line"].search(
            [
                ("product_id", "=", product.id),
                ("account_id", "=", self.account_valuation.id),
                ("credit", "=", 0.0),
                ("debit", "=", 0.0),
            ]
        )

    def test_costing_method_change_posts_no_self_entry(self):
        self.make_purchase()
        product = self.product_1
        category = product.categ_id
        self.assertEqual(category.property_cost_method, "fifo")

        moves_before = self.env["account.move"].search([])
        category.property_cost_method = "average"
        new_moves = self.env["account.move"].search([]) - moves_before

        self_entries = new_moves.line_ids.filtered(
            lambda aml: aml.account_id == self.account_valuation
        ).mapped("move_id")
        for move in self_entries:
            accounts = move.line_ids.mapped("account_id")
            self.assertNotEqual(
                accounts,
                self.account_valuation,
                "Entry posted from the stock account to itself: %s" % move.name,
            )

        # the value of the stock is unchanged, only the costing method moved
        val_stock_p1 = round(self.qty_po_p1 * self.price_p1, 2)
        val_stock_p2 = round(self.qty_po_p2 * self.price_p2, 2)
        self.check_account_valuation(val_stock_p1, val_stock_p2)
