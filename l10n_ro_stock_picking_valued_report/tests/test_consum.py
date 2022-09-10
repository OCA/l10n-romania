# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged

from .common import TestStockPickingValued

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockConsumn(TestStockPickingValued):
    def set_stock(self, product, qty):
        stock_quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", product.id),
                ("location_id", "=", self.location_warehouse.id),
            ]
        )
        if not stock_quant:
            stock_quant_obj = self.env["stock.quant"].with_context(inventory_mode=True)
            inventory = stock_quant_obj.create(
                {
                    "location_id": self.location_warehouse.id,
                    "product_id": product.id,
                    "inventory_quantity": qty,
                }
            )
            inventory._apply_inventory()
        else:
            stock_quant = stock_quant.with_context(inventory_mode=True)
            stock_quant.write(
                {
                    "inventory_quantity": qty,
                }
            )
            stock_quant._apply_inventory()

    def test_transfer(self):
        self.set_stock(self.product_mp, 1000)
        location_id = self.picking_type_transfer.default_location_src_id
        location_dest_id = self.picking_type_transfer.default_location_dest_id
        _logger.info("Start transfer")
        picking = self.trasfer(location_id, location_dest_id)
        _logger.info("Tranfer efectuat")
        self.assertEqual(picking.amount_untaxed, 100.0)
        self.assertEqual(picking.amount_tax, 0.0)
        self.assertEqual(picking.amount_total, 100.0)
        self.assertEqual(picking.move_line_ids.price_subtotal, 100.0)
        self.assertEqual(picking.move_line_ids.price_tax, 0.0)
        self.assertEqual(picking.move_line_ids.price_total, 100.0)

    def test_consume(self):
        self.set_stock(self.product_mp, 1000)
        _logger.info("Start consum produse")
        location_id = self.picking_type_transfer.default_location_src_id
        location_dest_id = self.picking_type_transfer.default_location_dest_id.copy(
            {"usage": "consume"}
        )
        picking = self.trasfer(location_id, location_dest_id)
        _logger.info("Consum facuta")
        self.assertEqual(picking.amount_untaxed, 100.0)
        self.assertEqual(picking.amount_tax, 0.0)
        self.assertEqual(picking.amount_total, 100.0)
        self.assertEqual(picking.move_line_ids.price_subtotal, 100.0)
        self.assertEqual(picking.move_line_ids.price_tax, 0.0)
        self.assertEqual(picking.move_line_ids.price_total, 100.0)
