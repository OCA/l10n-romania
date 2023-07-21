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
