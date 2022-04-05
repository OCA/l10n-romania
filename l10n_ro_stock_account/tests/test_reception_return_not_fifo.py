# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile la achizitie
import logging

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


class TestStockPurchaseReturn(TestStockCommon):
    def test_not_fifo_return(self):
        po1 = self.create_po(notice=False)
        self.create_invoice()
        _logger.info("PO1: %s" % po1.amount_total)
        _logger.info("Product1 price: %s" % self.product_1.standard_price)

        stock_value_p1 = round(self.qty_po_p1 * self.price_p1, 2)
        stock_value_p2 = round(self.qty_po_p2 * self.price_p2, 2)
        self.check_stock_valuation(stock_value_p1, stock_value_p2)

        self.price_p1 = 55.0
        po2 = self.create_po(notice=False)
        self.create_invoice()
        _logger.info("PO2: %s" % po2.amount_total)
        _logger.info("Product1 price: %s" % self.product_1.standard_price)

        stock_value_final_p1 = stock_value_p1 + round(self.qty_po_p1 * self.price_p1, 2)
        stock_value_final_p2 = stock_value_p2 + round(self.qty_po_p2 * self.price_p2, 2)
        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)

        pick = po2.picking_ids
        self.make_return(pick, 2)

        stock_value_final_p1 = stock_value_final_p1 - round(2 * self.price_p1, 2)
        stock_value_final_p2 = stock_value_final_p2 - round(2 * self.price_p2, 2)
        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)
