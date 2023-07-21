# Copyright (C) 2023 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile la achizitie
import logging

from odoo.tests import Form, tagged

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockSaleReturn(TestStockCommon):
    def test_not_fifo_return(self):
        """
        Test FIFO valuation method for stock accounting in case of return from sale
        """

        #  intrare in stoc
        self.make_purchase()

        stock_value_final_p1 = round(self.qty_po_p1 * self.price_p1, 2)
        stock_value_final_p2 = round(self.qty_po_p2 * self.price_p2, 2)

        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)
        self.check_account_valuation(stock_value_final_p1, stock_value_final_p2)

        # iesire din stoc prin vanzare
        self.create_so()

        # valoarea de stoc dupa vanzarea produselor
        stock_value_final_p1 = round(self.val_p1_i - self.val_stock_out_so_p1, 2)
        stock_value_final_p2 = round(self.val_p2_i - self.val_stock_out_so_p2, 2)

        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)
        self.check_account_valuation(stock_value_final_p1, stock_value_final_p2)

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

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=pick.ids, active_id=pick.ids[0], active_model="stock.picking"
            )
        )
        return_wiz = stock_return_picking_form.save()
        return_wiz.product_return_moves.write(
            {"quantity": 2.0, "to_refund": True}
        )  # Return only 2
        res = return_wiz.create_returns()
        return_pick = self.env["stock.picking"].browse(res["res_id"])

        # Validate picking
        return_pick.move_line_ids.write({"qty_done": 2})

        return_pick.button_validate()

        self.create_sale_invoice()

        stock_value_final_p1 += round(2 * price_p1, 2)
        stock_value_final_p2 += round(2 * price_p2, 2)

        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)
        self.check_account_valuation(stock_value_final_p1, stock_value_final_p2)

    def test_not_fifo_return2(self):
        """
        Test FIFO valuation method for stock accounting in case of return from sale

                        Cant	    Preț		    Valoare stoc
        achiziție       5	    50	    250	    250
        achiziție	    20	    75	    1500	1750
        vanzare	        -5	    50	    -250	1500
        vanzare	        -10	    75	    -750	750
        retur	        5	    50	    250	    1000
        retur	        2	    75	    150	    1150


        achiziție	    10  	50	    500 	500
        achiziție	    20  	75  	1500   	2000
        vanzare	        -10	    50	    -500	1500
        vanzare	        -5	    75	    -375	1125
        retur	        7	    50	    350	    1475

        """

        #  intrare in stoc

        self.qty_po_p1 = 5.0
        self.qty_po_p2 = 10.0

        self.price_p1 = 50.0
        self.price_p2 = 50.0
        self.make_purchase()

        stock_value_final_p1 = round(self.qty_po_p1 * self.price_p1, 2)
        stock_value_final_p2 = round(self.qty_po_p2 * self.price_p2, 2)

        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)
        self.check_account_valuation(stock_value_final_p1, stock_value_final_p2)

        self.qty_po_p1 = 20.0
        self.qty_po_p2 = 20.0
        self.price_p1 = 75.0
        self.price_p2 = 75.0
        self.make_purchase()
        stock_value_final_p1 += round(self.qty_po_p1 * self.price_p1, 2)
        stock_value_final_p2 += round(self.qty_po_p2 * self.price_p2, 2)

        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)
        self.check_account_valuation(stock_value_final_p1, stock_value_final_p2)

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

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=pick.ids, active_id=pick.ids[0], active_model="stock.picking"
            )
        )
        return_wiz = stock_return_picking_form.save()
        return_wiz.product_return_moves.write({"quantity": 7.0, "to_refund": True})
        res = return_wiz.create_returns()
        return_pick = self.env["stock.picking"].browse(res["res_id"])

        # Validate picking
        return_pick.move_line_ids.write({"qty_done": 7})

        return_pick.button_validate()

        self.create_sale_invoice()

        stock_value_final_p1 += round(5 * 50 + 2 * 75, 2)
        stock_value_final_p2 += round(7 * 50, 2)

        self.check_stock_valuation(stock_value_final_p1, stock_value_final_p2)
        self.check_account_valuation(stock_value_final_p1, stock_value_final_p2)
