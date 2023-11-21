# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile la achizitie
import logging

from odoo.tests import tagged

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockTransferLandedCost(TestStockCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super(TestStockTransferLandedCost, cls).setUpClass(
            chart_template_ref=chart_template_ref
        )

    def test_po_sale_lc_fifo(self):
        self.product_1.product_tmpl_id.categ_id.property_cost_method = "fifo"
        self.product_2.product_tmpl_id.categ_id.property_cost_method = "fifo"
        self._po_transfer_lc_test()

    def test_po_sale_lc_average(self):
        self.product_1.product_tmpl_id.categ_id.property_cost_method = "average"
        self.product_2.product_tmpl_id.categ_id.property_cost_method = "average"
        self._po_transfer_lc_test()

    def _po_transfer_lc_test(self):
        warehouse_1 = self.company_data["default_warehouse"]
        stock_location = warehouse_1.lot_stock_id
        acc_3024 = self.env["account.account"].search(
            [("code", "=", "302400")], limit=1
        )
        acc_3026 = self.env["account.account"].search(
            [("code", "=", "302600")], limit=1
        )

        self.product_1.categ_id.write({"l10n_ro_stock_account_change": True})
        # Stock Location 2
        stock_location2 = self.env["stock.location"].create(
            {
                "name": "Stock Location 2",
                "location_id": warehouse_1.view_location_id.id,
                "usage": "internal",
                "l10n_ro_property_stock_valuation_account_id": acc_3024.id,
                "valuation_in_account_id": acc_3024.id,
                "valuation_out_account_id": acc_3024.id,
            }
        )
        # Stock Location 3
        stock_location3 = self.env["stock.location"].create(
            {
                "name": "Stock Location 3",
                "location_id": warehouse_1.view_location_id.id,
                "usage": "internal",
                "l10n_ro_property_stock_valuation_account_id": acc_3026.id,
                "valuation_in_account_id": acc_3026.id,
                "valuation_out_account_id": acc_3026.id,
            }
        )
        #  intrare in stoc 10 buc p1
        round(self.qty_po_p1 * self.price_p1, 2)
        round(self.qty_po_p2 * self.price_p2, 2)
        po = self.create_po()
        income_ship = po.picking_ids
        self.check_account_valuation(0, 0)
        self.check_account_valuation(0, 0, self.account_expense)
        self.check_account_valuation(0, 0, self.account_landed_cost)
        self.check_account_valuation(0, 0, acc_3024)
        self.check_account_valuation(0, 0, acc_3026)

        # iesire din stoc prin transfer intern
        self.transfer(stock_location, stock_location2, product=self.product_1)
        int_transfer11 = self.picking
        self.check_account_valuation(-2 * self.price_p1, 0)
        self.check_account_valuation(0, 0, self.account_expense)
        self.check_account_valuation(0, 0, self.account_landed_cost)
        self.check_account_valuation(2 * self.price_p1, 0, acc_3024)
        self.check_account_valuation(0, 0, acc_3026)

        self.transfer(stock_location, stock_location2, product=self.product_2)
        int_transfer12 = self.picking
        self.check_account_valuation(-2 * self.price_p1, -2 * self.price_p2)
        self.check_account_valuation(0, 0, self.account_expense)
        self.check_account_valuation(0, 0, self.account_landed_cost)
        self.check_account_valuation(2 * self.price_p1, 2 * self.price_p2, acc_3024)
        self.check_account_valuation(0, 0, acc_3026)

        # iesire din stoc prin transfer intern
        self.transfer(stock_location2, stock_location3, product=self.product_1)
        int_transfer21 = self.picking
        self.check_account_valuation(-2 * self.price_p1, -2 * self.price_p2)
        self.check_account_valuation(0, 0, self.account_expense)
        self.check_account_valuation(0, 0, self.account_landed_cost)
        self.check_account_valuation(0, 2 * self.price_p2, acc_3024)
        self.check_account_valuation(2 * self.price_p1, 0, acc_3026)

        self.transfer(stock_location2, stock_location3, product=self.product_2)
        int_transfer22 = self.picking
        self.check_account_valuation(-2 * self.price_p1, -2 * self.price_p2)
        self.check_account_valuation(0, 0, self.account_expense)
        self.check_account_valuation(0, 0, self.account_landed_cost)
        self.check_account_valuation(0, 0, acc_3024)
        self.check_account_valuation(2 * self.price_p1, 2 * self.price_p2, acc_3026)

        self.create_lc(income_ship, 10, 10, product=self.landed_cost)
        self.create_invoice()
        self.check_account_valuation(8 * self.price_p1 + 8, 8 * self.price_p2 + 8)
        self.check_account_valuation(0, 0, self.account_expense)
        self.check_account_valuation(-10, -10, self.account_landed_cost)
        self.check_account_valuation(0, 0, acc_3024)
        self.check_account_valuation(
            2 * self.price_p1 + 2, 2 * self.price_p2 + 2, acc_3026
        )

        # verificare SVLs reception
        move_po_p1 = income_ship.move_lines.filtered(
            lambda mv: mv.product_id == self.product_1
        )
        move_po_p2 = income_ship.move_lines.filtered(
            lambda mv: mv.product_id == self.product_2
        )

        svls_in_p1 = move_po_p1.stock_valuation_layer_ids
        self.assertEqual(len(svls_in_p1), 2)

        svls_in_p2 = move_po_p2.stock_valuation_layer_ids
        self.assertEqual(len(svls_in_p2), 2)

        # 10 * 50 este primul svl reception (create de PO)
        # 10 este SVL creat de LC, si atasat de move-ul de receptie
        # -2 este SVL creat de LC, si atasat de move-ul de receptie,
        # iesire 2 buc prin transfer intern
        # 10 * 50 + 10 = 510 (p1_in_val)
        p1_in_val = self.qty_po_p1 * self.price_p1 + 10
        self.assertEqual(sum(svls_in_p1.mapped("value")), p1_in_val)

        p1_in_remaining_val = p1_in_val - (2 * self.price_p1) - 2  # 408
        self.assertEqual(svls_in_p1[0].remaining_qty, self.qty_po_p1 - 2)
        self.assertEqual(svls_in_p1[0].remaining_value, p1_in_remaining_val)

        p2_in_val = self.qty_po_p2 * self.price_p2 + 10
        self.assertEqual(sum(svls_in_p2.mapped("value")), p2_in_val)

        p2_in_remaining_val = p2_in_val - (2 * self.price_p2) - 2  # = 408
        self.assertEqual(svls_in_p1[0].remaining_qty, self.qty_po_p2 - 2)
        self.assertEqual(svls_in_p1[0].remaining_value, p2_in_remaining_val)

        # verificare SVLs primul transfer intern
        move_so_p1 = int_transfer11.move_lines.filtered(
            lambda mv: mv.product_id == self.product_1
        )
        move_so_p2 = int_transfer12.move_lines.filtered(
            lambda mv: mv.product_id == self.product_2
        )

        svls_out_p1 = move_so_p1.stock_valuation_layer_ids
        self.assertEqual(len(svls_out_p1), 4)
        svls_out_p1_minus = svls_out_p1.filtered(lambda svl: svl.value < 0)
        svls_out_p1_plus = svls_out_p1.filtered(lambda svl: svl.value > 0)

        # -(-2) * 50 este primul svl delivery (create de SO)
        # -2 este SVL creat de LC, si atasat de move-ul de delivery
        # (-2) * 50 - 2 = -102 (p1_out_final)
        p1_out_final = -2 * self.price_p1 - 2
        self.assertEqual(sum(svls_out_p1_minus.mapped("value")), p1_out_final)
        self.assertEqual(sum(svls_out_p1_plus.mapped("value")), -1 * p1_out_final)
        self.assertEqual(sum(svls_out_p1.mapped("remaining_qty")), 0)
        self.assertEqual(sum(svls_out_p1.mapped("remaining_value")), 0)

        svls_out_p2 = move_so_p2.stock_valuation_layer_ids
        # LC nu a creat nici un SVL in plus pentru product_2
        self.assertEqual(len(svls_out_p2), 4)
        svls_out_p2_minus = svls_out_p2.filtered(lambda svl: svl.value < 0)
        svls_out_p2_plus = svls_out_p2.filtered(lambda svl: svl.value > 0)

        # -10 este SVL creat de LC, si atasat de move-ul de delivery
        p2_out_final = -2 * self.price_p2 - 2
        self.assertEqual(sum(svls_out_p2_minus.mapped("value")), p2_out_final)
        self.assertEqual(sum(svls_out_p2_plus.mapped("value")), -1 * p2_out_final)
        self.assertEqual(sum(svls_out_p2.mapped("remaining_qty")), 0)
        self.assertEqual(sum(svls_out_p2.mapped("remaining_value")), 0)

        # verificare SVLs al doilea transfer intern
        move_so_p1 = int_transfer21.move_lines.filtered(
            lambda mv: mv.product_id == self.product_1
        )
        move_so_p2 = int_transfer22.move_lines.filtered(
            lambda mv: mv.product_id == self.product_2
        )

        svls_out_p1 = move_so_p1.stock_valuation_layer_ids
        self.assertEqual(len(svls_out_p1), 4)
        svls_out_p1_minus = svls_out_p1.filtered(lambda svl: svl.value < 0)
        svls_out_p1_plus = svls_out_p1.filtered(lambda svl: svl.value > 0)

        # -(-2) * 50 este primul svl delivery (create de SO)
        # -2 este SVL creat de LC, si atasat de move-ul de delivery
        # (-2) * 50 - 2 = -102 (p1_out_final)
        p1_out_final = (-1) * 2 * self.price_p1 - 2
        self.assertEqual(sum(svls_out_p1_minus.mapped("value")), p1_out_final)
        self.assertEqual(sum(svls_out_p1_plus.mapped("value")), -1 * p1_out_final)

        svls_out_p2 = move_so_p2.stock_valuation_layer_ids
        # LC nu a creat nici un SVL in plus pentru product_2
        self.assertEqual(len(svls_out_p2), 4)
        svls_out_p2_minus = svls_out_p2.filtered(lambda svl: svl.value < 0)
        svls_out_p2_plus = svls_out_p2.filtered(lambda svl: svl.value > 0)

        # -(-2) * 50 este primul svl delivery (create de SO)
        # -2 este SVL creat de LC, si atasat de move-ul de delivery
        # (-2) * 50 - 2 = -102 (p1_out_final)
        p2_out_final = (-1) * 2 * self.price_p2 - 2
        self.assertEqual(sum(svls_out_p2_minus.mapped("value")), p2_out_final)
        self.assertEqual(sum(svls_out_p2_plus.mapped("value")), -1 * p2_out_final)
