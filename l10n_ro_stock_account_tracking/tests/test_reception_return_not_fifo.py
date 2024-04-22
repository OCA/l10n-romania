# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile la achizitie
import logging

from odoo.tests import tagged

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockPurchaseReturn(TestStockCommon):
    def test_not_fifo_return(self):
        po1 = self.create_po()
        self.create_invoice()
        _logger.debug("PO1: %s" % po1.amount_total)
        _logger.debug("Product1 price: %s" % self.product_1.standard_price)

        stock_value_p1 = round(self.qty_po_p1 * self.price_p1, 2)
        stock_value_p2 = round(self.qty_po_p2 * self.price_p2, 2)

        self.check_stock_valuation(stock_value_p1, stock_value_p2)
        self.check_account_valuation(stock_value_p1, stock_value_p2)

        self.price_p1 = 55.0
        self.price_p2 = 55.0
        po2 = self.create_po()
        self.create_invoice()
        _logger.debug("PO2: %s" % po2.amount_total)
        _logger.debug("Product1 price: %s" % self.product_1.standard_price)

        stock_value_final_p1 = stock_value_p1 + round(self.qty_po_p1 * self.price_p1, 2)
        stock_value_final_p2 = stock_value_p2 + round(self.qty_po_p2 * self.price_p2, 2)
        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)
        self.check_account_valuation(stock_value_final_p1, stock_value_final_p2)
        pick = po2.picking_ids
        self.make_return(pick, 2)

        stock_value_final_p1 = stock_value_final_p1 - round(2 * self.price_p1, 2)
        stock_value_final_p2 = stock_value_final_p2 - round(2 * self.price_p2, 2)
        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)

        self.create_invoice()
        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)
        self.check_account_valuation(stock_value_final_p1, stock_value_final_p2)
