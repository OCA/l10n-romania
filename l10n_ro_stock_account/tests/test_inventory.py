# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockInventory(TestStockCommon):
    def _plus_inventory(self):
        self.make_purchase()

        inventory = self.env["stock.inventory"].create(
            {
                "location_ids": [(4, self.location_warehouse.id)],
                "product_ids": [(4, self.product_1.id)],
            }
        )
        inventory.action_start()
        inventory.line_ids.product_qty = self.qty_po_p1 + 10
        _logger.debug("start plus inventory")
        inventory.action_validate()

    def test_plus_inventory(self):
        self._plus_inventory()
        val_stock_p1 = round((self.qty_po_p1 + 10) * self.price_p1, 2)
        val_stock_p2 = round((self.qty_po_p2) * self.price_p2, 2)
        self.check_stock_valuation(val_stock_p1, val_stock_p2)
        self.check_account_valuation(val_stock_p1, val_stock_p2)

    def test_plus_inventory_location_valuation(self):
        self.set_warehouse_as_mp()
        self._plus_inventory()

    def _minus_inventory(self):
        self.make_purchase()

        inventory = self.env["stock.inventory"].create(
            {
                "location_ids": [(4, self.location_warehouse.id)],
                "product_ids": [(4, self.product_1.id)],
            }
        )
        inventory.action_start()

        inventory.line_ids.product_qty = self.qty_po_p1 - 10
        _logger.debug("start minus inventory")
        inventory.action_validate()

    def test_minus_inventory(self):
        self._minus_inventory()

        val_stock_p1 = round((self.qty_po_p1 - 10) * self.price_p1, 2)
        val_stock_p2 = round((self.qty_po_p2) * self.price_p2, 2)

        self.check_stock_valuation(val_stock_p1, val_stock_p2)
        self.check_account_valuation(val_stock_p1, val_stock_p2)

    def test_minus_inventory_location_valuation(self):
        self.set_warehouse_as_mp()
        self._minus_inventory()
