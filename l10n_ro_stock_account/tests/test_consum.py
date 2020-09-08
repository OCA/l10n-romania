# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


# Generare note contabile la achizitie


class TestStockConsumn(TestStockCommon):
    def set_stock(self, product, qty):
        inventory = self.env["stock.inventory"].create(
            {
                "location_ids": [(4, self.location_warehouse.id)],
                "product_ids": [(4, product.id)],
            }
        )
        inventory.action_start()

        inventory.line_ids.product_qty = qty
        inventory.action_validate()

    def trasfer(self, location_id, location_dest_id):
        self.picking_type = self.env.ref("stock.picking_type_internal")
        self.PickingObj = self.env["stock.picking"]
        self.MoveObj = self.env["stock.move"]

        picking = self.PickingObj.create(
            {
                "picking_type_id": self.picking_type.id,
                "location_id": location_id.id,
                "location_dest_id": location_dest_id.id,
            }
        )
        self.MoveObj.create(
            {
                "name": self.product_1.name,
                "product_id": self.product_1.id,
                "product_uom_qty": 1,
                "product_uom": self.product_1.uom_id.id,
                "picking_id": picking.id,
                "location_id": location_id.id,
                "location_dest_id": location_dest_id.id,
            }
        )
        picking.action_confirm()
        picking.action_assign()
        for move_line in picking.move_lines:
            if move_line.product_uom_qty > 0 and move_line.quantity_done == 0:
                move_line.write({"quantity_done": move_line.product_uom_qty})
        picking.action_done()

    def test_transfer(self):
        # la transferul dintr-o locatie in alta valoarea stocului trebuei sa ramana neschimbata
        #  daca se transfera stocul in
        self.picking_type = self.env.ref("stock.picking_type_internal")
        self.set_stock(self.product_mp, 1000)
        location_id = self.picking_type.default_location_src_id
        location_dest_id = self.picking_type.default_location_dest_id
        _logger.info("Start transfer")
        self.trasfer(location_id, location_dest_id)
        _logger.info("Tranfer efectuat")

    def test_consumption(self):
        self.picking_type = self.env.ref("stock.picking_type_internal")
        self.set_stock(self.product_mp, 1000)
        _logger.info("Start Consum in productie")
        location_id = self.picking_type.default_location_src_id
        location_dest_id = self.env["stock.location"].search(
            [("usage", "=", "production")], limit=1
        )
        self.trasfer(location_id, location_dest_id)
        _logger.info("Consum in productie facut")

    def test_production(self):
        self.picking_type = self.env.ref("stock.picking_type_internal")
        self.set_stock(self.product_mp, 1000)
        _logger.info("Start receptie din productie")
        location_id = self.env["stock.location"].search(
            [("usage", "=", "production")], limit=1
        )
        location_dest_id = self.picking_type.default_location_dest_id
        self.trasfer(location_id, location_dest_id)
        _logger.info("Receptie  din productie facuta")

    def test_usage_giving(self):
        self.picking_type = self.env.ref("stock.picking_type_internal")
        self.set_stock(self.product_mp, 1000)
        _logger.info("Start dare in folosinta")
        location_id = self.picking_type.default_location_src_id
        location_dest_id = self.env["stock.location"].search(
            [("usage", "=", "usage_giving")], limit=1
        )
        self.trasfer(location_id, location_dest_id)
        _logger.info("Dare in folosinta facuta")
