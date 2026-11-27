# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


class CostChangeCases:
    """A cost change after the goods left the stock (a bill at another price
    than the reception) makes core replay the valuation and correct the
    entries already posted; only the difference may be posted again."""

    def _expense_balance(self):
        expense = self.product_fifo.categ_id.property_account_expense_categ_id
        lines = self.env["account.move.line"].search(
            [
                ("account_id", "=", expense.id),
                ("product_id", "=", self.product_fifo.id),
                ("parent_state", "=", "posted"),
                ("move_id.move_type", "=", "entry"),
            ]
        )
        return sum(lines.mapped("balance"))

    def test_cost_change_posts_only_difference(self):
        self.create_purchase(
            {
                "currency_id": self.ron,
                "partner_id": self.supplier_1,
                "product_id": self.product_fifo,
                "qty": 10,
                "stock_qty": 10,
                "inv_qty": 0,
                "price": 100,
                "index": "cost_change_po",
            }
        )
        purchase = self.purchase_order_cost_change_po
        sale = self.create_sale_order(
            {
                "currency_id": self.ron,
                "partner_id": self.customer_1,
                "product_id": self.product_fifo,
                "qty": 5,
                "stock_qty": 5,
                "inv_qty": 0,
                "price": 150,
                "advance": 0,
                "discount": 0,
                "index": "cost_change_so",
            }
        )
        out_move = sale.picking_ids.move_ids.filtered(lambda m: m.state == "done")
        self.assertAlmostEqual(self._expense_balance(), 500.0)

        # Bill the reception at 120 instead of 100.
        purchase.action_create_invoice()
        bill = purchase.invoice_ids
        bill.invoice_date = bill.date = purchase.date_order
        bill.invoice_line_ids.price_unit = 120
        bill.action_post()

        out_move.invalidate_recordset(["value"])
        self.assertAlmostEqual(abs(out_move.value), 600.0)
        self.assertAlmostEqual(
            self._expense_balance(),
            600.0,
            msg="The replay must post the 100 difference, not the whole entry.",
        )
