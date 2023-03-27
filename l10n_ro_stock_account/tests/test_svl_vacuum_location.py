# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile la achizitie
import logging

from odoo.tests import tagged

from .common import TestStockCommon as RoTestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestSVLVacuumLocation(RoTestStockCommon):
    def test_fifo_negative_1(self):
        self.product_1.categ_id.property_cost_method = "fifo"
        self.product_1.product_tmpl_id.standard_price = 8.0
        self.warehouse_1 = self.company_data["default_warehouse"]
        self.stock_location = self.warehouse_1.lot_stock_id
        self.supplier_location = self.env.ref("stock.stock_location_suppliers")
        self.customer_location = self.env.ref("stock.stock_location_customers")
        self.categ_unit = self.env.ref("uom.product_uom_categ_unit")
        self.uom_unit = self.env["uom.uom"].search(
            [("category_id", "=", self.categ_unit.id), ("uom_type", "=", "reference")],
            limit=1,
        )

        # Stock Location 2
        self.stock_location2 = self.env["stock.location"].create(
            {
                "name": "Stock Location 2",
                "location_id": self.warehouse_1.view_location_id.id,
            }
        )

        # ---------------------------------------------------------------------
        # Receive 40 units @ 8, in stock location 2
        # ---------------------------------------------------------------------
        move_in_loc2 = self.env["stock.move"].create(
            {
                "name": "40 in @15",
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location2.id,
                "product_id": self.product_1.id,
                "product_uom": self.uom_unit.id,
                "product_uom_qty": 40.0,
                "price_unit": 8.0,
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_1.id,
                            "location_id": self.supplier_location.id,
                            "location_dest_id": self.stock_location2.id,
                            "product_uom_id": self.uom_unit.id,
                            "qty_done": 40.0,
                        },
                    )
                ],
            }
        )
        move_in_loc2._action_confirm()
        move_in_loc2._action_done()

        # ---------------------------------------------------------------------
        # Send 50 units you don't have from main stock location
        # ---------------------------------------------------------------------
        move_out_loc1 = self.env["stock.move"].create(
            {
                "name": "50 out",
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_1.id,
                "product_uom": self.uom_unit.id,
                "product_uom_qty": 50.0,
                "price_unit": 0,
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_1.id,
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.customer_location.id,
                            "product_uom_id": self.uom_unit.id,
                            "qty_done": 50.0,
                        },
                    )
                ],
            }
        )
        move_out_loc1._action_confirm()
        move_out_loc1._action_done()

        self.assertEqual(move_out_loc1.stock_valuation_layer_ids.value, -400.0)

        self.assertEqual(
            move_out_loc1.stock_valuation_layer_ids.remaining_qty, -50.0
        )  # normally unused in out moves, but as it moved negative stock we mark it

        self.assertEqual(
            move_out_loc1.stock_valuation_layer_ids.unit_cost,
            self.product_1.product_tmpl_id.standard_price,
        )

        # ---------------------------------------------------------------------
        # Receive 40 units @ 15 in main stock location
        # ---------------------------------------------------------------------
        move_in_loc1 = self.env["stock.move"].create(
            {
                "name": "40 in @15",
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.product_1.id,
                "product_uom": self.uom_unit.id,
                "product_uom_qty": 40.0,
                "price_unit": 15.0,
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_1.id,
                            "location_id": self.supplier_location.id,
                            "location_dest_id": self.stock_location.id,
                            "product_uom_id": self.uom_unit.id,
                            "qty_done": 40.0,
                        },
                    )
                ],
            }
        )
        move_in_loc1._action_confirm()
        move_in_loc1._action_done()

        # stock values for move2
        self.assertEqual(move_in_loc1.stock_valuation_layer_ids.value, 600.0)
        self.assertEqual(move_in_loc1.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move_in_loc1.stock_valuation_layer_ids.unit_cost, 15.0)

        # ---------------------------------------------------------------------
        # The vacuum ran
        # ---------------------------------------------------------------------
        # account values after vacuum -> credit 371
        valuation_aml = self._get_stock_valuation_move_lines()
        vacuum1_valuation_aml = valuation_aml[-1]
        self.assertEqual(vacuum1_valuation_aml.debit, 0)
        # 280 was credited more in valuation (we compensated 40 items here,
        # so initially 40 were valued at 8 -> 320 in credit but now we actually
        # sent 40@15 = 600,
        # so the difference is 280 more credited)
        self.assertEqual(vacuum1_valuation_aml.credit, 280)

        # account values after vacuum -> credit 371 -> debit 607
        output_aml = self._get_stock_output_move_lines()
        vacuum1_output_aml = output_aml[-1]
        self.assertEqual(vacuum1_output_aml.debit, 280)
        self.assertEqual(vacuum1_output_aml.credit, 0)
