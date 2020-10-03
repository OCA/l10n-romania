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

    def test_transfer(self):
        # la transferul dintr-o locatie in alta valoarea stocului trebuie
        # sa ramana neschimbata

        self.set_stock(self.product_mp, 1000)
        location_id = self.picking_type_transfer.default_location_src_id
        location_dest_id = self.picking_type_transfer.default_location_dest_id
        _logger.info("Start transfer")
        picking = self.trasfer(location_id, location_dest_id)
        _logger.info("Tranfer efectuat")

        _logger.info("Start return transfer")
        self.make_return(picking, 1)

    def test_transfer_in_locatie_evaluata(self):
        # transfer materia prima in marfa

        self.set_stock(self.product_mp, 1000)
        location_id = self.picking_type_transfer.default_location_src_id
        location_dest_id = self.picking_type_transfer.default_location_dest_id.copy(
            {"property_stock_valuation_account_id": self.account_valuation.id}
        )
        _logger.info("Start transfer")
        picking = self.trasfer(location_id, location_dest_id)
        _logger.info("Tranfer efectuat")

        _logger.info("Start return transfer")
        self.make_return(picking, 1)

    def test_transfer_din_locatie_evaluata(self):
        # transfer materia prima in marfa

        self.set_stock(self.product_mp, 1000)
        location_id = self.picking_type_transfer.default_location_src_id.copy(
            {"property_stock_valuation_account_id": self.account_valuation.id}
        )
        location_dest_id = self.picking_type_transfer.default_location_dest_id

        _logger.info("Start transfer")
        picking = self.trasfer(location_id, location_dest_id)
        _logger.info("Tranfer efectuat")

        _logger.info("Start return transfer")
        self.make_return(picking, 1)

    def test_production_consumption(self):
        self.set_stock(self.product_mp, 1000)
        _logger.info("Start Consum in productie")
        location_id = self.picking_type_transfer.default_location_src_id

        picking = self.trasfer(location_id, self.location_production)
        _logger.info("Consum in productie facut")

        _logger.info("Start retur  consum")
        self.make_return(picking, 1)

    def test_consumption_din_locatie_evaluata(self):
        self.set_stock(self.product_mp, 1000)
        _logger.info("Start Consum in productie din locatie cu alta evaluare")
        location_id = self.picking_type_transfer.default_location_src_id.copy(
            {
                "property_stock_valuation_account_id": self.account_valuation_mp.id,
                "property_account_expense_location_id": self.account_expense_mp.id,
            }
        )

        picking = self.trasfer(location_id, self.location_production)
        _logger.info("Consum in productie facut")

        _logger.info("Start retur  consum")
        self.make_return(picking, 1)

    def test_production(self):
        self.set_stock(self.product_mp, 1000)
        _logger.info("Start receptie din productie")

        location_dest_id = self.picking_type_transfer.default_location_dest_id
        picking = self.trasfer(self.location_production, location_dest_id)
        _logger.info("Receptie  din productie facuta")

        _logger.info("Start retur  in productie")
        self.make_return(picking, 1)

    def test_usage_giving(self):

        self.set_stock(self.product_mp, 1000)
        _logger.info("Start dare in folosinta")

        location_id = self.picking_type_transfer.default_location_src_id

        location_dest_id = self.picking_type_transfer.default_location_dest_id.copy(
            {"usage": "usage_giving"}
        )

        picking = self.trasfer(location_id, location_dest_id)
        _logger.info("Dare in folosinta facuta")

        _logger.info("Start retur dare in folosinta")
        self.make_return(picking, 1)

    def test_consume(self):

        self.set_stock(self.product_mp, 1000)
        _logger.info("Start consum produse")

        location_id = self.picking_type_transfer.default_location_src_id

        location_dest_id = self.picking_type_transfer.default_location_dest_id.copy(
            {"usage": "consume"}
        )

        picking = self.trasfer(location_id, location_dest_id)
        _logger.info("Consum facuta")

        _logger.info("Start retur consum")
        self.make_return(picking, 1)
