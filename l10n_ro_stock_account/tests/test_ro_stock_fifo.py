# Copyright (C) 2020 Terrabit
# Copyright (C) 2025 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from contextlib import closing

from odoo.tests import tagged

from .common import TestROStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockFifo(TestROStockCommon):
    def test_ro_stock_product_fifo(self):
        filename = "test_cases_fifo.csv"
        test_cases = self.read_test_cases_from_csv_file(filename)
        for _key, case in test_cases.items():
            _logger.info(
                "Running test case: %s - %s", case.get("code"), case.get("name")
            )
            with self.subTest(case=case), closing(self.cr.savepoint()):
                self.test_case(case)

    def test_ro_search_remaining_qty_per_location(self):
        """Verify that ``search([('remaining_qty', '=', True)])`` returns the
        same moves as the per-location ``_compute_remaining_qty`` computes,
        across normal FIFO consumption and negative-stock compensation."""
        self.env.company.fifo_per_location = True
        self.env.company.fifo_location_negative_compensation = True

        def search_remaining():
            return self.env["stock.move"].search(
                [
                    ("remaining_qty", "=", True),
                    ("product_id", "=", self.product_fifo.id),
                    ("state", "=", "done"),
                ]
            )

        # --- Scenario A: Normal FIFO consumption ---
        # PO 5@100 → 1 IN move with remaining_qty=5
        self.create_purchase(
            {
                "currency_id": self.ron,
                "partner_id": self.supplier_1,
                "product_id": self.product_fifo,
                "qty": 5,
                "stock_qty": 5,
                "inv_qty": 5,
                "price": 100,
                "inv_price": 100,
                "index": "srq_po1",
            }
        )
        po1_move = self.env["stock.move"].search(
            [
                ("product_id", "=", self.product_fifo.id),
                ("is_in", "=", True),
                ("state", "=", "done"),
                ("location_dest_id", "=", self.location.id),
            ],
            limit=1,
        )
        self.assertTrue(po1_move, "PO IN move should exist after purchase")
        results = search_remaining()
        self.assertIn(
            po1_move,
            results,
            "Fresh PO IN move must be returned by search_remaining_qty",
        )
        self.assertAlmostEqual(po1_move.remaining_qty, 5.0)

        # SALE 3 → PO has remaining_qty=2 left
        self.create_sale_order(
            {
                "currency_id": self.ron,
                "partner_id": self.customer_1,
                "product_id": self.product_fifo,
                "qty": 3,
                "stock_qty": 3,
                "inv_qty": 3,
                "price": 150,
                "inv_price": 150,
                "advance": 0,
                "discount": 0,
                "index": "srq_so1",
            }
        )
        po1_move.invalidate_recordset(["remaining_qty"])
        results = search_remaining()
        self.assertIn(
            po1_move,
            results,
            "Partially consumed PO IN must still be in search results",
        )
        self.assertAlmostEqual(po1_move.remaining_qty, 2.0)

        # SALE 2 more → PO fully consumed, remaining_qty=0
        self.create_sale_order(
            {
                "currency_id": self.ron,
                "partner_id": self.customer_1,
                "product_id": self.product_fifo,
                "qty": 2,
                "stock_qty": 2,
                "inv_qty": 2,
                "price": 150,
                "inv_price": 150,
                "advance": 0,
                "discount": 0,
                "index": "srq_so2",
            }
        )
        po1_move.invalidate_recordset(["remaining_qty"])
        results = search_remaining()
        self.assertNotIn(
            po1_move, results, "Fully consumed PO IN must NOT be in search results"
        )
        self.assertAlmostEqual(po1_move.remaining_qty, 0.0)

        # --- Scenario B: Negative stock + compensation ---
        # Stock = 0. SALE 3 → creates negative stock on the OUT move
        # (fifo_neg_pending_qty=3, no IN remaining anywhere).
        self.create_sale_order(
            {
                "currency_id": self.ron,
                "partner_id": self.customer_1,
                "product_id": self.product_fifo,
                "qty": 3,
                "stock_qty": 3,
                "inv_qty": 3,
                "price": 150,
                "inv_price": 150,
                "advance": 0,
                "discount": 0,
                "index": "srq_so3",
            }
        )
        results = search_remaining()
        self.assertFalse(
            results,
            "No IN move should have remaining_qty>0 after full consumption "
            "even when an OUT created negative stock",
        )

        # PO 5@100 → compensates the negative; PO should have remaining_qty=2
        # (5 incoming - 3 compensated for the previous OUT)
        self.create_purchase(
            {
                "currency_id": self.ron,
                "partner_id": self.supplier_1,
                "product_id": self.product_fifo,
                "qty": 5,
                "stock_qty": 5,
                "inv_qty": 5,
                "price": 100,
                "inv_price": 100,
                "index": "srq_po2",
            }
        )
        po2_move = self.env["stock.move"].search(
            [
                ("product_id", "=", self.product_fifo.id),
                ("is_in", "=", True),
                ("state", "=", "done"),
                ("location_dest_id", "=", self.location.id),
            ],
            order="id desc",
            limit=1,
        )
        po2_move.invalidate_recordset(["remaining_qty"])
        results = search_remaining()
        self.assertIn(
            po2_move, results, "PO IN after compensation must be returned by search"
        )
        self.assertAlmostEqual(
            po2_move.remaining_qty,
            2.0,
            msg="PO IN should have 2 buc remaining (5 in - 3 compensated)",
        )
