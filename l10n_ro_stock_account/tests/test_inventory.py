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

        inventory_obj = self.env["stock.quant"].with_context(inventory_mode=True)
        inventory = inventory_obj.create(
            {
                "location_id": self.location_warehouse.id,
                "product_id": self.product_1.id,
                "inventory_quantity": self.qty_po_p1 + 10,
            }
        )
        inventory._apply_inventory()

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

        inventory_obj = self.env["stock.quant"].with_context(inventory_mode=True)
        inventory = inventory_obj.create(
            {
                "location_id": self.location_warehouse.id,
                "product_id": self.product_1.id,
                "inventory_quantity": self.qty_po_p1 - 10,
            }
        )
        inventory._apply_inventory()

    def test_minus_inventory(self):
        self._minus_inventory()

        val_stock_p1 = round((self.qty_po_p1 - 10) * self.price_p1, 2)
        val_stock_p2 = round((self.qty_po_p2) * self.price_p2, 2)

        self.check_stock_valuation(val_stock_p1, val_stock_p2)
        self.check_account_valuation(val_stock_p1, val_stock_p2)

    def test_minus_inventory_location_valuation(self):
        self.set_warehouse_as_mp()
        self._minus_inventory()
