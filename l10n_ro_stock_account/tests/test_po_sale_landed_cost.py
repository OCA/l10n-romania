# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile la achizitie
import logging

from odoo.tests import tagged

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockSaleLandedCost(TestStockCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super(TestStockSaleLandedCost, cls).setUpClass(
            chart_template_ref=chart_template_ref
        )

    def test_po_sale_lc_fifo(self):
        self.product_1.product_tmpl_id.categ_id.property_cost_method = "fifo"
        self.product_2.product_tmpl_id.categ_id.property_cost_method = "fifo"
        self._po_sale_lc_test()

    def test_po_sale_lc_average(self):
        self.product_1.product_tmpl_id.categ_id.property_cost_method = "average"
        self.product_2.product_tmpl_id.categ_id.property_cost_method = "average"
        self._po_sale_lc_test()

    def _po_sale_lc_test(self):
        """ """
        #  intrare in stoc 10 buc p1
        po = self.create_po()
        income_ship = po.picking_ids

        # iesire din stoc prin vanzare 2 buc p1
        self.qty_so_p1 = 2

        # iesire din stock prin vanzare 10 buc p2
        self.qty_so_p2 = self.qty_po_p2
        out_ship = self.create_so()
        self.create_lc(income_ship, 10, 10)

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
        # 10 * 50 + 10 = 510 (p1_in_val)
        p1_in_val = self.qty_po_p1 * self.price_p1 + 10
        self.assertEqual(sum(svls_in_p1.mapped("value")), p1_in_val)

        p1_in_remaining_val = p1_in_val - (self.qty_so_p1 * self.price_p1) - 2  # 408
        self.assertEqual(svls_in_p1[0].remaining_value, p1_in_remaining_val)

        p2_in_val = self.qty_po_p2 * self.price_p2 + 10
        self.assertEqual(sum(svls_in_p2.mapped("value")), p2_in_val)

        p2_in_remaining_val = p2_in_val - (self.qty_so_p2 * self.price_p2) - 10  # = 0
        self.assertEqual(p2_in_remaining_val, 0)
        self.assertEqual(svls_in_p2[0].remaining_value, p2_in_remaining_val)

        # verificare SVLs delivery
        move_so_p1 = out_ship.move_lines.filtered(
            lambda mv: mv.product_id == self.product_1
        )
        move_so_p2 = out_ship.move_lines.filtered(
            lambda mv: mv.product_id == self.product_2
        )

        svls_out_p1 = move_so_p1.stock_valuation_layer_ids
        self.assertEqual(len(svls_out_p1), 2)

        # -(-2) * 50 este primul svl delivery (create de SO)
        # -2 este SVL creat de LC, si atasat de move-ul de delivery
        # (-2) * 50 - 2 = -102 (p1_out_final)
        p1_out_final = (-1) * self.qty_so_p1 * self.price_p1 - 2
        self.assertEqual(sum(svls_out_p1.mapped("value")), p1_out_final)

        svls_out_p2 = move_so_p2.stock_valuation_layer_ids
        # LC nu a creat nici un SVL in plus pentru product_2
        self.assertEqual(len(svls_out_p2), 2)

        # -10 este SVL creat de LC, si atasat de move-ul de delivery
        p2_out_final = (-1) * self.qty_so_p2 * self.price_p2 - 10
        self.assertEqual(sum(svls_out_p2.mapped("value")), p2_out_final)
