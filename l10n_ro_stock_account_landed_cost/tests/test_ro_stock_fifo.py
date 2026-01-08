# Copyright (C) 2020 Terrabit
# Copyright (C) 2025 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import os
from contextlib import closing

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockFifo(TestROStockCommon):
    @TestROStockCommon.setup_country("ro")
    def setUp(cls):
        super().setUp()
        cls.l10n_ro_cost_type = "normal"

    def test_ro_stock_product_fifo(self):
        module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filename = "test_cases_fifo.csv"
        test_cases = self.read_test_cases_from_csv_file(filename, module_dir=module_dir)
        for _key, case in test_cases.items():
            _logger.info(
                "Running test case: %s - %s", case.get("code"), case.get("name")
            )
            with self.subTest(case=case), closing(self.cr.savepoint()):
                self.test_case(case)

    def test_button_create_landed_costs(self):
        purchase = self.env["purchase.order"].create(
            {
                "partner_id": self.supplier_1.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_fifo.id,
                            "product_qty": 1.0,
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )
        purchase.button_confirm()
        picking = purchase.picking_ids
        picking.move_ids._set_quantity_done(1.0)
        picking.button_validate()

        invoice = (
            self.env["account.move"]
            .with_context(default_move_type="in_invoice")
            .create(
                {
                    "move_type": "in_invoice",
                    "partner_id": self.supplier_1.id,
                    "invoice_date": purchase.date_order,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.landed_cost.id,
                                "price_unit": 50.0,
                                "quantity": 1.0,
                                "purchase_line_id": purchase.order_line[0].id,
                            },
                        )
                    ],
                }
            )
        )
        invoice.action_post()

        # Apelăm metoda button_create_landed_costs
        action = invoice.button_create_landed_costs()
        self.assertEqual(action.get("res_model"), "stock.landed.cost")

        landed_cost = self.env["stock.landed.cost"].browse(action.get("res_id"))
        self.assertTrue(landed_cost.exists())
        self.assertEqual(landed_cost.vendor_bill_id, invoice)
        self.assertIn(picking, landed_cost.picking_ids)
