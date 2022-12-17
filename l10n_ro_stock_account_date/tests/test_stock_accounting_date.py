# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockAccountDate(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_inventory(self):
        self.make_purchase()
        acc_date = fields.Date.today() - timedelta(days=1)
        inventory = self.env["stock.inventory"].create(
            {
                "location_ids": [(4, self.location_warehouse.id)],
                "product_ids": [(4, self.product_1.id)],
                "accounting_date": acc_date,
            }
        )
        inventory.action_start()
        inventory.line_ids.product_qty = self.qty_po_p1 + 20
        _logger.info("start inventory")
        inventory.action_validate()
        stock_move = inventory.move_ids
        self.assertEqual(inventory.accounting_date, acc_date)
        self.assertEqual(stock_move.date.date(), acc_date)
        self.assertEqual(stock_move.move_line_ids.date.date(), acc_date)
        self.assertEqual(
            stock_move.stock_valuation_layer_ids.create_date.date(), acc_date
        )
        self.assertTrue(stock_move.account_move_ids)
        self.assertEqual(stock_move.account_move_ids.date, acc_date)

    def test_transfer(self):
        self.set_stock(self.product_mp, 1000)
        acc_date = fields.Date.today() - timedelta(days=1)
        location_id = self.picking_type_transfer.default_location_src_id
        location_dest_id = self.picking_type_transfer.default_location_dest_id.copy(
            {"l10n_ro_property_stock_valuation_account_id": self.account_valuation.id}
        )
        _logger.info("Start transfer")
        self.transfer(location_id, location_dest_id, accounting_date=acc_date)
        picking = self.picking
        stock_move = picking.move_lines
        _logger.info("Tranfer efectuat")
        self.assertEqual(picking.l10n_ro_accounting_date.date(), acc_date)
        self.assertEqual(stock_move.date.date(), acc_date)
        self.assertEqual(stock_move.move_line_ids.date.date(), acc_date)
        self.assertEqual(
            stock_move.stock_valuation_layer_ids.mapped("create_date")[0].date(),
            acc_date,
        )
        self.assertEqual(stock_move.account_move_ids.date, acc_date)
