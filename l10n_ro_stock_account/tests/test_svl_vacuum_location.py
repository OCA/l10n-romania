# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile la achizitie
import logging

from odoo.tests import tagged

from .common import TestStockCommon as RoTestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestSVLVacuumLocation(RoTestStockCommon):
    def setUp(self):
        super().setUp()
        set_param = self.env["ir.config_parameter"].sudo().set_param
        set_param("l10n_ro_stock_account.simple_valuation", "False")
        self.simple_valuation = False

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
        output_aml = self._get_stock_valuation_move_lines(self.account_expense)
        vacuum1_output_aml = output_aml[-1]
        self.assertEqual(vacuum1_output_aml.debit, 280)
        self.assertEqual(vacuum1_output_aml.credit, 0)

    def test_fifo_negative_location(self):
        self.product_1.categ_id.property_cost_method = "fifo"
        self.product_1.product_tmpl_id.standard_price = 8.0
        self.warehouse_1 = self.company_data["default_warehouse"]
        self.stock_location = self.warehouse_1.lot_stock_id
        self.account_valuation_copy = self.account_valuation.copy({"code": "37100"})
        self.account_expense_copy = self.account_expense.copy({"code": "607001"})
        self.stock_location_2 = self.env["stock.location"].create(
            {
                "name": "Test Location Internal",
                "usage": "internal",
                "company_id": self.env.company.id,
                "l10n_ro_property_stock_valuation_account_id": self.account_valuation_copy.id,
                "l10n_ro_property_account_expense_location_id": self.account_expense_copy.id,
            }
        )
        self.supplier_location = self.env.ref("stock.stock_location_suppliers")
        self.customer_location = self.env.ref("stock.stock_location_customers")
        self.categ_unit = self.env.ref("uom.product_uom_categ_unit")
        self.uom_unit = self.env["uom.uom"].search(
            [("category_id", "=", self.categ_unit.id), ("uom_type", "=", "reference")],
            limit=1,
        )

        # ---------------------------------------------------------------------
        # Send 50 units you don't have from main stock location
        # ---------------------------------------------------------------------
        move_out_loc1 = self.env["stock.move"].create(
            {
                "name": "50 out",
                "location_id": self.stock_location_2.id,
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
                            "location_id": self.stock_location_2.id,
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

        move_out_loc2 = self.env["stock.move"].create(
            {
                "name": "20 out",
                "location_id": self.stock_location_2.id,
                "location_dest_id": self.customer_location.id,
                "product_id": self.product_1.id,
                "product_uom": self.uom_unit.id,
                "product_uom_qty": 20.0,
                "price_unit": 0,
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_1.id,
                            "location_id": self.stock_location_2.id,
                            "location_dest_id": self.customer_location.id,
                            "product_uom_id": self.uom_unit.id,
                            "qty_done": 20.0,
                        },
                    )
                ],
            }
        )
        move_out_loc2._action_confirm()
        move_out_loc2._action_done()

        self.assertEqual(move_out_loc2.stock_valuation_layer_ids.value, -160.0)

        self.assertEqual(
            move_out_loc2.stock_valuation_layer_ids.remaining_qty, -20.0
        )  # normally unused in out moves, but as it moved negative stock we mark it

        self.assertEqual(
            move_out_loc2.stock_valuation_layer_ids.unit_cost,
            self.product_1.product_tmpl_id.standard_price,
        )

        # ---------------------------------------------------------------------
        # Receive 40 units @ 15 in main stock location
        # ---------------------------------------------------------------------
        move_in_loc1 = self.env["stock.move"].create(
            {
                "name": "100 in @15",
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.product_1.id,
                "product_uom": self.uom_unit.id,
                "product_uom_qty": 100.0,
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
                            "qty_done": 100.0,
                        },
                    )
                ],
            }
        )
        move_in_loc1._action_confirm()
        move_in_loc1._action_done()

        # stock values for move2
        self.assertEqual(move_in_loc1.stock_valuation_layer_ids.value, 1500.0)
        self.assertEqual(move_in_loc1.stock_valuation_layer_ids.remaining_qty, 100)
        self.assertEqual(move_in_loc1.stock_valuation_layer_ids.unit_cost, 15.0)

        move_internal_loc1 = self.env["stock.move"].create(
            {
                "name": "40 internal @15",
                "location_id": self.stock_location.id,
                "location_dest_id": self.stock_location_2.id,
                "product_id": self.product_1.id,
                "product_uom": self.uom_unit.id,
                "product_uom_qty": 40.0,
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_1.id,
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.stock_location_2.id,
                            "product_uom_id": self.uom_unit.id,
                            "qty_done": 40.0,
                        },
                    )
                ],
            }
        )
        move_internal_loc1._action_confirm()
        move_internal_loc1._action_done()

        self.assertEqual(
            sum(move_internal_loc1.stock_valuation_layer_ids.mapped("value")), 0
        )
        self.assertEqual(
            sum(move_internal_loc1.stock_valuation_layer_ids.mapped("remaining_qty")), 0
        )
        self.assertEqual(
            sum(move_internal_loc1.stock_valuation_layer_ids.mapped("remaining_value")),
            0,
        )
        # account values after internal transfer -> credit 371
        valuation_aml = self._get_stock_valuation_move_lines()
        vacuum1_valuation_aml = valuation_aml[-1]
        self.assertEqual(vacuum1_valuation_aml.debit, 0)
        self.assertEqual(vacuum1_valuation_aml.credit, 600)

        # account values after vacuum -> credit 371 -> debit 607
        stock_acc_aml = self._get_stock_valuation_move_lines(
            self.account_valuation_copy
        )
        for aml in stock_acc_aml:
            _logger.info(aml)
            _logger.info(aml.debit)
            _logger.info(aml.credit)
            _logger.info(aml.name)
        self.assertEqual(stock_acc_aml[0].debit, 0)
        self.assertEqual(stock_acc_aml[0].credit, 400)
        self.assertEqual(stock_acc_aml[0].name, "50 out - Product A")
        self.assertEqual(stock_acc_aml[1].debit, 0)
        self.assertEqual(stock_acc_aml[1].credit, 160)
        self.assertEqual(stock_acc_aml[1].name, "20 out - Product A")
        self.assertEqual(stock_acc_aml[2].debit, 600)
        self.assertEqual(stock_acc_aml[2].credit, 0)
        self.assertEqual(stock_acc_aml[2].name, "40 internal @15 - Product A")
        self.assertEqual(stock_acc_aml[3].debit, 0)
        self.assertEqual(stock_acc_aml[3].credit, 280)
        # -400 -160 + 600 - 280 = -240 = 30 bucati la 8 lei
        self.assertEqual(
            stock_acc_aml[3].name, "Revaluation of False (negative inventory)"
        )
        self.assertEqual(
            sum(move_out_loc1.stock_valuation_layer_ids.mapped("value")), -680.0
        )
        self.assertEqual(
            sum(move_out_loc1.stock_valuation_layer_ids.mapped("remaining_qty")), -10.0
        )
        self.assertEqual(
            sum(move_out_loc2.stock_valuation_layer_ids.mapped("value")), -160.0
        )
        self.assertEqual(
            sum(move_out_loc2.stock_valuation_layer_ids.mapped("remaining_qty")), -20.0
        )
        self.check_stock_valuation(900.0, 0.0)

        move_internal_loc1 = self.env["stock.move"].create(
            {
                "name": "20 internal @15",
                "location_id": self.stock_location.id,
                "location_dest_id": self.stock_location_2.id,
                "product_id": self.product_1.id,
                "product_uom": self.uom_unit.id,
                "product_uom_qty": 20.0,
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_1.id,
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.stock_location_2.id,
                            "product_uom_id": self.uom_unit.id,
                            "qty_done": 20.0,
                        },
                    )
                ],
            }
        )
        move_internal_loc1._action_confirm()
        move_internal_loc1._action_done()

        self.assertEqual(
            sum(move_internal_loc1.stock_valuation_layer_ids.mapped("value")), 0
        )
        self.assertEqual(
            sum(move_internal_loc1.stock_valuation_layer_ids.mapped("remaining_qty")),
            0,
        )
        self.assertEqual(
            sum(move_internal_loc1.stock_valuation_layer_ids.mapped("remaining_value")),
            0,
        )
        # account values after internal transfer -> credit 371
        valuation_aml = self._get_stock_valuation_move_lines()
        vacuum1_valuation_aml = valuation_aml[-1]
        self.assertEqual(vacuum1_valuation_aml.debit, 0)
        self.assertEqual(vacuum1_valuation_aml.credit, 300)
        stock_acc_aml = self._get_stock_valuation_move_lines(
            self.account_valuation_copy
        )
        for aml in stock_acc_aml:
            _logger.info(aml)
            _logger.info(aml.debit)
            _logger.info(aml.credit)
            _logger.info(aml.name)
        self.assertEqual(stock_acc_aml[0].debit, 0)
        self.assertEqual(stock_acc_aml[0].credit, 400)
        self.assertEqual(stock_acc_aml[0].name, "50 out - Product A")
        self.assertEqual(stock_acc_aml[1].debit, 0)
        self.assertEqual(stock_acc_aml[1].credit, 160)
        self.assertEqual(stock_acc_aml[1].name, "20 out - Product A")
        self.assertEqual(stock_acc_aml[2].debit, 600)
        self.assertEqual(stock_acc_aml[2].credit, 0)
        self.assertEqual(stock_acc_aml[2].name, "40 internal @15 - Product A")
        self.assertEqual(stock_acc_aml[3].debit, 0)
        self.assertEqual(stock_acc_aml[3].credit, 280)
        self.assertEqual(
            stock_acc_aml[3].name, "Revaluation of False (negative inventory)"
        )
        self.assertEqual(stock_acc_aml[4].debit, 300)
        self.assertEqual(stock_acc_aml[4].credit, 0)
        self.assertEqual(stock_acc_aml[4].name, "20 internal @15 - Product A")
        self.assertEqual(stock_acc_aml[5].debit, 0)
        self.assertEqual(stock_acc_aml[5].credit, 70)
        self.assertEqual(
            stock_acc_aml[5].name, "Revaluation of False (negative inventory)"
        )
        self.assertEqual(stock_acc_aml[6].debit, 0)
        self.assertEqual(stock_acc_aml[6].credit, 70)
        self.assertEqual(
            stock_acc_aml[6].name, "Revaluation of False (negative inventory)"
        )

        self.assertEqual(
            sum(move_out_loc1.stock_valuation_layer_ids.mapped("value")), -750.0
        )

        self.assertEqual(
            sum(move_out_loc1.stock_valuation_layer_ids.mapped("remaining_qty")), 0
        )
        self.assertEqual(
            sum(move_out_loc2.stock_valuation_layer_ids.mapped("value")), -230.0
        )

        self.assertEqual(
            sum(move_out_loc2.stock_valuation_layer_ids.mapped("remaining_qty")), -10
        )
        self.check_stock_valuation(600.0, 0.0)
        self.check_stock_valuation(-80.0, 0.0, self.account_valuation_copy)

        move_internal_loc3 = self.env["stock.move"].create(
            {
                "name": "30 internal @15",
                "location_id": self.stock_location.id,
                "location_dest_id": self.stock_location_2.id,
                "product_id": self.product_1.id,
                "product_uom": self.uom_unit.id,
                "product_uom_qty": 30.0,
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_1.id,
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.stock_location_2.id,
                            "product_uom_id": self.uom_unit.id,
                            "qty_done": 30.0,
                        },
                    )
                ],
            }
        )
        move_internal_loc3._action_confirm()
        move_internal_loc3._action_done()

        # account values after internal transfer -> credit 371
        valuation_aml = self._get_stock_valuation_move_lines()
        vacuum1_valuation_aml = valuation_aml[-1]
        self.assertEqual(vacuum1_valuation_aml.debit, 0)
        self.assertEqual(vacuum1_valuation_aml.credit, 450)
        stock_acc_aml = self._get_stock_valuation_move_lines(
            self.account_valuation_copy
        )
        self.assertEqual(stock_acc_aml[0].debit, 0)
        self.assertEqual(stock_acc_aml[0].credit, 400)
        self.assertEqual(stock_acc_aml[0].name, "50 out - Product A")
        self.assertEqual(stock_acc_aml[1].debit, 0)
        self.assertEqual(stock_acc_aml[1].credit, 160)
        self.assertEqual(stock_acc_aml[1].name, "20 out - Product A")
        self.assertEqual(stock_acc_aml[2].debit, 600)
        self.assertEqual(stock_acc_aml[2].credit, 0)
        self.assertEqual(stock_acc_aml[2].name, "40 internal @15 - Product A")
        self.assertEqual(stock_acc_aml[3].debit, 0)
        self.assertEqual(stock_acc_aml[3].credit, 280)
        self.assertEqual(
            stock_acc_aml[3].name, "Revaluation of False (negative inventory)"
        )
        self.assertEqual(stock_acc_aml[4].debit, 300)
        self.assertEqual(stock_acc_aml[4].credit, 0)
        self.assertEqual(stock_acc_aml[4].name, "20 internal @15 - Product A")
        self.assertEqual(stock_acc_aml[5].debit, 0)
        self.assertEqual(stock_acc_aml[5].credit, 70)
        self.assertEqual(
            stock_acc_aml[5].name, "Revaluation of False (negative inventory)"
        )
        self.assertEqual(stock_acc_aml[6].debit, 0)
        self.assertEqual(stock_acc_aml[6].credit, 70)
        self.assertEqual(
            stock_acc_aml[6].name, "Revaluation of False (negative inventory)"
        )
        self.assertEqual(stock_acc_aml[7].debit, 450)
        self.assertEqual(stock_acc_aml[7].credit, 0)
        self.assertEqual(stock_acc_aml[7].name, "30 internal @15 - Product A")
        self.assertEqual(stock_acc_aml[8].debit, 0)
        self.assertEqual(stock_acc_aml[8].credit, 70)
        self.assertEqual(
            stock_acc_aml[8].name, "Revaluation of False (negative inventory)"
        )

        self.assertEqual(
            sum(move_out_loc1.stock_valuation_layer_ids.mapped("value")), -750.0
        )
        self.assertEqual(
            sum(move_out_loc1.stock_valuation_layer_ids.mapped("remaining_value")), 0
        )
        self.assertEqual(
            sum(move_out_loc1.stock_valuation_layer_ids.mapped("remaining_qty")), 0
        )
        self.assertEqual(
            sum(move_out_loc2.stock_valuation_layer_ids.mapped("value")), -300
        )
        self.assertEqual(
            sum(move_out_loc2.stock_valuation_layer_ids.mapped("remaining_value")), 0
        )
        self.assertEqual(
            sum(move_out_loc2.stock_valuation_layer_ids.mapped("remaining_qty")), 0
        )

        self.assertEqual(
            sum(move_internal_loc3.stock_valuation_layer_ids.mapped("value")), 0
        )
        self.assertEqual(
            sum(move_internal_loc3.stock_valuation_layer_ids.mapped("remaining_qty")),
            20,
        )
        self.assertEqual(
            sum(move_internal_loc3.stock_valuation_layer_ids.mapped("remaining_value")),
            300,
        )
        self.check_stock_valuation(150.0, 0.0)
        self.check_stock_valuation(300.0, 0.0, self.account_valuation_copy)
