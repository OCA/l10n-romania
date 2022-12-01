# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


# Generare note contabile la achizitie


@tagged("post_install", "-at_install")
class TestStockConsum(TestStockCommon):
    def test_transfer(self):
        # la transferul dintr-o locatie in alta valoarea stocului trebuie
        # sa ramana neschimbata

        self.set_stock(self.product_mp, 1000)
        location_id = self.picking_type_transfer.default_location_src_id
        location_dest_id = self.picking_type_transfer.default_location_dest_id
        _logger.debug("Start transfer")
        self.transfer(location_id, location_dest_id)
        _logger.debug("Tranfer efectuat")

        _logger.debug("Start return transfer")
        self.make_return(self.picking, 1)

    def test_transfer_in_locatie_evaluata(self):
        # transfer materia prima in marfa

        self.set_stock(self.product_mp, 1000)
        location_id = self.picking_type_transfer.default_location_src_id
        location_dest_id = self.picking_type_transfer.default_location_dest_id.copy(
            {"l10n_ro_property_stock_valuation_account_id": self.account_valuation.id}
        )
        _logger.debug("Start transfer")
        self.transfer(location_id, location_dest_id)
        _logger.debug("Tranfer efectuat")

        _logger.debug("Start return transfer")
        self.make_return(self.picking, 1)

    def test_transfer_din_locatie_evaluata(self):
        # transfer materia prima in marfa

        self.set_stock(self.product_mp, 1000)
        location_id = self.picking_type_transfer.default_location_src_id.copy(
            {"l10n_ro_property_stock_valuation_account_id": self.account_valuation.id}
        )
        location_dest_id = self.picking_type_transfer.default_location_dest_id

        _logger.debug("Start transfer")
        self.transfer(location_id, location_dest_id)
        _logger.debug("Tranfer efectuat")

        _logger.debug("Start return transfer")
        self.make_return(self.picking, 1)

    def test_production_consumption(self):
        self.set_stock(self.product_mp, 1000)
        _logger.debug("Start Consum in productie")
        location_id = self.picking_type_transfer.default_location_src_id

        self.transfer(location_id, self.location_production)
        _logger.debug("Consum in productie facut")

        _logger.debug("Start retur  consum")
        self.make_return(self.picking, 1)

    def test_consumption_din_locatie_evaluata(self):
        self.set_stock(self.product_mp, 1000)
        _logger.debug("Start Consum in productie din locatie cu alta evaluare")
        location_id = self.picking_type_transfer.default_location_src_id.copy(
            {
                "l10n_ro_property_stock_valuation_account_id": self.account_valuation_mp.id,
                "l10n_ro_property_account_expense_location_id": self.account_expense_mp.id,
            }
        )

        self.transfer(location_id, self.location_production)
        _logger.debug("Consum in productie facut")

        _logger.debug("Start retur  consum")
        self.make_return(self.picking, 1)

    def test_production(self):
        self.set_stock(self.product_mp, 1000)
        _logger.debug("Start receptie din productie")

        location_dest_id = self.picking_type_transfer.default_location_dest_id
        self.transfer(self.location_production, location_dest_id)
        _logger.debug("Receptie  din productie facuta")

        _logger.debug("Start retur  in productie")
        self.make_return(self.picking, 1)

    def test_usage_giving(self):

        self.set_stock(self.product_mp, 1000)
        _logger.debug("Start dare in folosinta")

        location_id = self.picking_type_transfer.default_location_src_id

        location_dest_id = self.picking_type_transfer.default_location_dest_id.copy(
            {"usage": "usage_giving"}
        )

        self.transfer(location_id, location_dest_id)
        _logger.debug("Dare in folosinta facuta")

        _logger.debug("Start retur dare in folosinta")
        self.make_return(self.picking, 1)

    def test_consume(self):

        self.set_stock(self.product_mp, 1000)
        _logger.debug("Start consum produse")

        location_id = self.picking_type_transfer.default_location_src_id

        location_dest_id = self.picking_type_transfer.default_location_dest_id.copy(
            {"usage": "consume"}
        )

        self.transfer(location_id, location_dest_id)
        _logger.debug("Consum facuta")

        _logger.debug("Start retur consum")
        self.make_return(self.picking, 1)

    def test_consume_extra_accounts(self):
        acc_3028 = self.env["account.account"].search(
            [("code", "=", "302800")], limit=1
        )
        acc_6028 = self.env["account.account"].search(
            [("code", "=", "602800")], limit=1
        )
        self.account_valuation_mp.l10n_ro_stock_consume_account_id = acc_3028
        self.account_expense_mp.l10n_ro_stock_consume_account_id = acc_6028
        self.product_mp.standard_price = self.price_p1
        val_stock_p1 = -1 * round(4 * self.price_p1, 2)

        self.set_stock(self.product_mp, 4)
        self.check_stock_valuation(val_stock_p1, 0)
        self.check_account_valuation(val_stock_p1, 0, self.account_valuation_mp)
        self.check_account_valuation(0, 0, acc_3028)
        self.check_account_valuation(0, 0, acc_6028)

        _logger.info("Start consum produse")
        location_id = self.picking_type_transfer.default_location_src_id
        location_dest_id = self.picking_type_transfer.default_location_dest_id.copy(
            {"usage": "consume"}
        )
        self.transfer(location_id, location_dest_id)
        _logger.info("Consum facuta")

        self.check_stock_valuation(val_stock_p1 / 2, 0)
        self.check_account_valuation(val_stock_p1 / 2, 0, self.account_valuation_mp)
        self.check_account_valuation(0, 0, acc_3028)
        self.check_account_valuation(val_stock_p1 / 2, 0, acc_6028)

        _logger.info("Start retur consum")
        self.make_return(self.picking, 1)
        self.check_stock_valuation(val_stock_p1, 0)
        self.check_account_valuation(val_stock_p1, 0, self.account_valuation_mp)
        self.check_account_valuation(0, 0, acc_3028)
        self.check_account_valuation(0, 0, acc_6028)

    def test_usage_giving_extra_accounts(self):
        acc_3028 = self.env["account.account"].search(
            [("code", "=", "302800")], limit=1
        )
        acc_6028 = self.env["account.account"].search(
            [("code", "=", "602800")], limit=1
        )
        self.account_valuation_mp.l10n_ro_stock_consume_account_id = acc_3028
        self.account_expense_mp.l10n_ro_stock_consume_account_id = acc_6028
        self.product_mp.standard_price = self.price_p1
        val_stock_p1 = -1 * round(4 * self.price_p1, 2)

        self.set_stock(self.product_mp, 4)
        self.check_stock_valuation(val_stock_p1, 0)
        self.check_account_valuation(val_stock_p1, 0, self.account_valuation_mp)
        self.check_account_valuation(0, 0, acc_3028)
        self.check_account_valuation(0, 0, acc_6028)

        _logger.info("Start dare in folosinta")
        location_id = self.picking_type_transfer.default_location_src_id
        location_dest_id = self.picking_type_transfer.default_location_dest_id.copy(
            {"usage": "usage_giving"}
        )
        self.transfer(location_id, location_dest_id)
        _logger.info("Dare in folosinta facuta")

        self.check_stock_valuation(val_stock_p1 / 2, 0)
        self.check_account_valuation(val_stock_p1 / 2, 0)
        self.check_account_valuation(0, 0, acc_3028)
        self.check_account_valuation(val_stock_p1 / 2, 0, acc_6028)

        _logger.info("Start retur dare in folosinta")
        self.make_return(self.picking, 1)
        self.check_stock_valuation(val_stock_p1, 0)
        self.check_account_valuation(val_stock_p1, 0)
        self.check_account_valuation(0, 0, acc_3028)
        self.check_account_valuation(0, 0, acc_6028)

    def test_consume_extra_location_accounts(self):
        acc_3026 = self.env["account.account"].search(
            [("code", "=", "302600")], limit=1
        )
        acc_6026 = self.env["account.account"].search(
            [("code", "=", "602600")], limit=1
        )
        acc_707 = self.env["account.account"].search([("code", "=", "707000")], limit=1)
        _logger.info(
            "Start consum produse cand conturile de pe categorie difera de cele de pe locatie"
        )
        self.product_mp.standard_price = self.price_p1
        self.product_mp.categ_id.write({"l10n_ro_stock_account_change": True})
        val_stock_p1 = 1 * round(4 * self.price_p1, 2)

        self.set_stock(self.product_mp, 4)
        self.check_account_valuation_mp(val_stock_p1, self.account_valuation_mp)
        self.check_stock_valuation(val_stock_p1, 0)

        _logger.info("Start consum produse")
        location_id = self.picking_type_transfer.default_location_src_id
        location_id.write(
            {
                "l10n_ro_property_account_income_location_id": acc_707,
                "l10n_ro_property_account_expense_location_id": acc_6026,
                "l10n_ro_property_stock_valuation_account_id": acc_3026,
            }
        )
        location_dest_id = self.picking_type_transfer.default_location_dest_id.copy(
            {"usage": "consume"}
        )

        self.transfer(location_id, location_dest_id, self.product_mp)
        _logger.info("Consum facut")
        self.check_account_valuation_mp(-val_stock_p1 / 2, acc_3026)
        self.check_account_valuation_mp(val_stock_p1 / 2, acc_6026)
