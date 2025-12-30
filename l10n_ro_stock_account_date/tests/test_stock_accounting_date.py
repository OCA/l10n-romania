# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockAccountDate(TestROStockCommon):
    @TestROStockCommon.setup_country("ro")
    def setUp(cls):
        super().setUp()
        cls.product_fifo.standard_price = 100.0

    def make_purchase(self):
        po_step = {
            "name": "Receptie + inventar cu data contabila",
            "code": "1",
            "steps": [
                {
                    "case_no": "1",
                    "type": "purchase",
                    "currency_id": self.env.company.currency_id,
                    "partner_id": self.supplier_1,
                    "product_id": self.product_fifo,
                    "step": 1,
                    "qty": 10.0,
                    "stock_qty": 10.0,
                    "inv_qty": 10.0,
                    "price": 100.0,
                    "inv_price": 100.0,
                    "checks": {
                        "stock": {
                            "product_fifo": [
                                {"location": "location", "qty": 10, "value": 1000}
                            ]
                        },
                        "account": {"371000": 1000},
                    },
                    "name": "Receptie + inventar cu data contabila",
                },
            ],
        }
        self.run_test_step(po_step)

    def make_inventory(self):
        inventory_obj = self.env["stock.quant"].with_context(inventory_mode=True)
        inventory = inventory_obj.create(
            {
                "location_id": self.location.id,
                "product_id": self.product_fifo.id,
                "inventory_quantity": 15,
            }
        )
        return inventory

    def make_transfer(self):
        int_picking_type = self.location.warehouse_id.int_type_id
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": int_picking_type.id,
                "location_id": self.location.id,
                "location_dest_id": self.location1.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_fifo.id,
                            "product_uom_qty": 5,
                            "product_uom": self.product_fifo.uom_id.id,
                            "location_id": self.location.id,
                            "location_dest_id": self.location1.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids._set_quantity_done(5)
        return picking

    def test_inventory_accounting_date_future(self):
        # Test restrictie inventar cu data contabila in viitor
        self.make_purchase()
        inventory = self.make_inventory()
        acc_date = fields.Date.today() + timedelta(days=1)
        with self.assertRaises(UserError):
            inventory.accounting_date = acc_date
            inventory._apply_inventory()

    def test_inventory_accounting_date_last_month(self):
        # Test restrictie inventar cu data contabila in luna anterioara
        self.make_purchase()
        inventory = self.make_inventory()
        acc_date = fields.Date.today() - relativedelta(months=2)
        with self.assertRaises(UserError):
            self.env.company.l10n_ro_restrict_stock_move_date_last_month = True
            inventory.accounting_date = acc_date
            inventory._apply_inventory()

    def test_inventory_accounting_date_lock_date(self):
        # Test restrictie inventar cu data contabila lock date
        self.make_purchase()
        inventory = self.make_inventory()
        acc_date = fields.Date.today() - relativedelta(months=1)
        with self.assertRaisesRegex(UserError, "locked fiscal period"):
            lock_date = fields.Date.today().replace(day=1) - timedelta(days=1)
            self.env.company.write(
                {
                    "sale_lock_date": lock_date,
                    "purchase_lock_date": lock_date,
                    "tax_lock_date": lock_date,
                }
            )
            inventory.accounting_date = acc_date
            inventory._apply_inventory()

    def test_inventory_accounting_date(self):
        # Test inventar efectuat cu data contabila
        self.make_purchase()
        inventory = self.make_inventory()
        acc_date = fields.Date.today() - timedelta(days=1)
        inventory.accounting_date = acc_date
        inventory._apply_inventory()
        stock_move = self.env["stock.move"].search(
            [
                (
                    "location_id",
                    "=",
                    inventory.product_id.with_company(
                        inventory.company_id
                    ).property_stock_inventory.id,
                ),
                ("product_id", "=", inventory.product_id.id),
            ]
        )
        self.assertEqual(stock_move.date.date(), acc_date)
        self.assertEqual(
            any(
                move_line.date.date() == acc_date
                for move_line in stock_move.move_line_ids
            ),
            True,
        )
        self.assertTrue(stock_move.account_move_id)
        self.assertEqual(stock_move.account_move_id.date, acc_date)

    def test_transfer_accounting_date_future(self):
        # Test restrictie transfer cu data contabila in viitor
        self.make_purchase()
        picking = self.make_transfer()
        acc_date = fields.Date.today() + timedelta(days=1)
        with self.assertRaises(UserError):
            picking.l10n_ro_accounting_date = acc_date
            picking.button_validate()

    def test_transfer_accounting_date_last_month(self):
        # Test restrictie transfer cu data contabila in luna anterioara
        self.make_purchase()
        picking = self.make_transfer()
        acc_date = fields.Date.today() - relativedelta(months=2)
        with self.assertRaises(UserError):
            self.env.company.l10n_ro_restrict_stock_move_date_last_month = True
            picking.l10n_ro_accounting_date = acc_date
            picking.button_validate()

    def test_transfer_accounting_date_lock_date(self):
        # Test restrictie transfer cu data contabila lock date
        self.make_purchase()
        picking = self.make_transfer()
        acc_date = fields.Date.today() - relativedelta(months=1)
        with self.assertRaisesRegex(UserError, "locked fiscal period"):
            lock_date = fields.Date.today().replace(day=1) - timedelta(days=1)
            self.env.company.write(
                {
                    "sale_lock_date": lock_date,
                    "purchase_lock_date": lock_date,
                    "tax_lock_date": lock_date,
                }
            )
            picking.l10n_ro_accounting_date = acc_date
            picking.button_validate()

    def test_transfer_accounting_date(self):
        # Test transfer efectuat cu data contabila
        self.make_purchase()
        picking = self.make_transfer()
        acc_date = fields.Date.today() - timedelta(days=1)
        picking.l10n_ro_accounting_date = acc_date
        picking.button_validate()
        stock_move = picking.move_ids[0]
        self.assertEqual(picking.l10n_ro_accounting_date.date(), acc_date)
        self.assertEqual(stock_move.date.date(), acc_date)
        self.assertEqual(
            any(
                move_line.date.date() == acc_date
                for move_line in stock_move.move_line_ids
            ),
            True,
        )
        self.assertTrue(stock_move.account_move_id)
        self.assertEqual(stock_move.account_move_id.date, acc_date)
