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

    def create_lc(self, picking, lc_p1, lc_p2):
        default_vals = self.env["stock.landed.cost"].default_get(
            list(self.env["stock.landed.cost"].fields_get())
        )
        default_vals.update(
            {
                "picking_ids": [picking.id],
                "account_journal_id": self.company_data["default_journal_misc"],
                "cost_lines": [(0, 0, {"product_id": self.product_1.id})],
                "valuation_adjustment_lines": [],
            }
        )
        cost_lines_values = {
            "name": ["equal split"],
            "split_method": ["equal"],
            "price_unit": [lc_p1 + lc_p2],
        }
        stock_landed_cost_1 = self.env["stock.landed.cost"].new(default_vals)
        for index, cost_line in enumerate(stock_landed_cost_1.cost_lines):
            cost_line.onchange_product_id()
            cost_line.name = cost_lines_values["name"][index]
            cost_line.split_method = cost_lines_values["split_method"][index]
            cost_line.price_unit = cost_lines_values["price_unit"][index]
        vals = stock_landed_cost_1._convert_to_write(stock_landed_cost_1._cache)
        stock_landed_cost_1 = self.env["stock.landed.cost"].create(vals)

        stock_landed_cost_1.compute_landed_cost()
        stock_landed_cost_1.button_validate()

    def test_po_sale_lc(self):
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
