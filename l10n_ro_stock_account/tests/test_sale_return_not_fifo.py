# Copyright (C) 2023 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile la achizitie
import logging

from odoo.tests import tagged

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockSaleReturn(TestStockCommon):
    def test_not_fifo_return1(self):
        """
        Test FIFO valuation method for stock accounting in case of return from sale
        """

        #  intrare in stoc
        self.make_purchase()

        stock_value_final_p1 = round(self.qty_po_p1 * self.price_p1, 2)
        stock_value_final_p2 = round(self.qty_po_p2 * self.price_p2, 2)

        # iesire din stoc prin vanzare
        self.create_so()

        # valoarea de stoc dupa vanzarea produselor
        stock_value_final_p1 -= self.val_stock_out_so_p1
        stock_value_final_p2 -= self.val_stock_out_so_p2

        price_p1 = self.price_p1
        price_p2 = self.price_p2

        self.price_p1 = 75.0
        self.price_p2 = 75.0
        self.make_purchase()
        stock_value_final_p1 += round(self.qty_po_p1 * self.price_p1, 2)
        stock_value_final_p2 += round(self.qty_po_p2 * self.price_p2, 2)

        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)
        self.check_account_valuation(stock_value_final_p1, stock_value_final_p2)

        pick = self.so.picking_ids

        self.make_return(pick, 2.0)

        self.create_sale_invoice()

        stock_value_final_p1 += round(2 * price_p1, 2)
        stock_value_final_p2 += round(2 * price_p2, 2)

        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)
        self.check_account_valuation(stock_value_final_p1, stock_value_final_p2)

    def test_not_fifo_return2(self):
        """
        Test FIFO valuation method for stock accounting in case of return from sale

        Test case vanzare
        Achizitie 5 buc la 50 lei
        Achizitie 20 buc la 75 lei
        Vanzare 15 buc
        Retur partial 7 buc
            Rezultat asteptat - revin 5 cu 50 lei si 2 cu 75 lei.
        Retur partial 1 buc
            Rezultat asteptat - revine 1 buc cu 75 lei pe stoc.


                        Cant	    Preț		    Valoare stoc
        achiziție       5	    50	    250	    250
        achiziție	    20	    75	    1500	1750
        vanzare        -15
         -vanzare	    -5	    50	    -250	1500
         -vanzare	    -10	    75	    -750	750
        retur1          7
         -retur	        5	    50	    250	    1000
         -retur	        2	    75	    150	    1150
        retur2
         -retur	        1	    75	    75	    1550


        """

        self.qty_po_p1 = 5.0
        self.qty_po_p2 = 10.0

        self.price_p1 = 50.0
        self.price_p2 = 50.0
        self.make_purchase()

        stock_value_final_p1 = round(self.qty_po_p1 * self.price_p1, 2)
        stock_value_final_p2 = round(self.qty_po_p2 * self.price_p2, 2)

        self.qty_po_p1 = 20.0
        self.qty_po_p2 = 20.0
        self.price_p1 = 75.0
        self.price_p2 = 75.0
        self.make_purchase()
        stock_value_final_p1 += round(self.qty_po_p1 * self.price_p1, 2)
        stock_value_final_p2 += round(self.qty_po_p2 * self.price_p2, 2)

        self.qty_so_p1 = 15.0
        self.qty_so_p2 = 15.0

        # iesire din stoc prin vanzare
        self.create_so()

        # valoarea de stoc dupa vanzarea produselor
        stock_value_final_p1 -= round(5 * 50 + 10 * 75, 2)
        stock_value_final_p2 -= round(10 * 50 + 5 * 75, 2)

        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)
        self.check_account_valuation(stock_value_final_p1, stock_value_final_p2)

        pick = self.so.picking_ids
        self.make_return(pick, 7.0)

        self.create_sale_invoice()

        stock_value_final_p1 += round(5 * 50 + 2 * 75, 2)
        stock_value_final_p2 += round(7 * 50, 2)

        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)
        self.check_account_valuation(stock_value_final_p1, stock_value_final_p2)

        self.make_return(pick, 1)

        stock_value_final_p1 += round(75, 2)
        stock_value_final_p2 += round(50, 2)

        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)
        self.check_account_valuation(stock_value_final_p1, stock_value_final_p2)
