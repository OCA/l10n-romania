# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from .common import TestROStockCommon


@tagged("post_install", "-at_install")
class TestROStockFifoCorrection(TestROStockCommon):
    """A FIFO out move whose quantity is edited after validation must be
    revalued (``move.value``) proportionally to the corrected quantity, for
    companies using ``fifo_per_location``."""

    def _deliver_five_from_ten(self):
        # Receive 10 @ 100 in stock.
        self.create_purchase(
            {
                "currency_id": self.ron,
                "partner_id": self.supplier_1,
                "product_id": self.product_fifo,
                "qty": 10,
                "stock_qty": 10,
                "inv_qty": 10,
                "price": 100,
                "inv_price": 100,
                "index": "corr_po",
            }
        )
        # Deliver 5 -> OUT move valued 5 * 100 = 500.
        sale = self.create_sale_order(
            {
                "currency_id": self.ron,
                "partner_id": self.customer_1,
                "product_id": self.product_fifo,
                "qty": 5,
                "stock_qty": 5,
                "inv_qty": 5,
                "price": 150,
                "inv_price": 150,
                "advance": 0,
                "discount": 0,
                "index": "corr_so",
            }
        )
        move = sale.picking_ids.move_ids.filtered(
            lambda m: m.product_id == self.product_fifo and m.state == "done"
        )
        self.assertEqual(len(move), 1)
        self.assertAlmostEqual(abs(move.value), 500.0)
        return move

    def test_fifo_correction_increase(self):
        move = self._deliver_five_from_ten()
        move_line = move.move_line_ids[:1]
        # Correct the consumption up by 1 (6 units) after validation.
        move_line.write({"quantity": move_line.quantity + 1})
        move.invalidate_recordset(["value"])
        self.assertAlmostEqual(
            abs(move.value),
            600.0,
            msg="Increasing a done FIFO out move must revalue it (5->6 @100).",
        )

    def test_fifo_correction_decrease(self):
        move = self._deliver_five_from_ten()
        move_line = move.move_line_ids[:1]
        # Correct the consumption down by 2 (3 units) after validation.
        move_line.write({"quantity": move_line.quantity - 2})
        move.invalidate_recordset(["value"])
        self.assertAlmostEqual(
            abs(move.value),
            300.0,
            msg="Decreasing a done FIFO out move must revalue it (5->3 @100).",
        )

    def test_fifo_correction_no_error_without_correction(self):
        """Writing a non-quantity field on a done out move must not raise from
        the correction path (regression: _set_value signature)."""
        move = self._deliver_five_from_ten()
        # A no-op quantity write (same value) still goes through the correction
        # code path and must not raise.
        move_line = move.move_line_ids[:1]
        move_line.write({"quantity": move_line.quantity})
        move.invalidate_recordset(["value"])
        self.assertAlmostEqual(abs(move.value), 500.0)
