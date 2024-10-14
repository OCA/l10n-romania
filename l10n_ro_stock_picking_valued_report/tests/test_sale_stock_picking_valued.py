# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from .common import TestStockPickingValued


@tagged("post_install", "-at_install")
class TestSaleStockPickingValued(TestStockPickingValued):
    def test_01_confirm_order(self):
        self.sale_order.action_confirm()
        self.assertTrue(len(self.sale_order.picking_ids))
        for picking in self.sale_order.picking_ids:
            picking.action_assign()
            self.assertEqual(picking.l10n_ro_amount_untaxed, 0)
            self.assertEqual(picking.l10n_ro_amount_tax, 0)
            self.assertEqual(picking.l10n_ro_amount_total, 0)

    def test_02_confirm_order(self):
        """Valued picking isn't computed if not reserved"""
        self.sale_order.action_confirm()
        for picking in self.sale_order.picking_ids:
            picking.action_assign()
            self.assertEqual(picking.l10n_ro_amount_untaxed, 0.0)
            self.assertEqual(picking.l10n_ro_amount_tax, 0.0)
            self.assertEqual(picking.l10n_ro_amount_total, 0.0)
            picking.do_unreserve()
            self.assertEqual(picking.l10n_ro_amount_untaxed, 0.0)
            self.assertEqual(picking.l10n_ro_amount_tax, 0.0)
            self.assertEqual(picking.l10n_ro_amount_total, 0.0)

    def test_03_tax_rounding_method(self):
        self.sale_order.company_id.tax_calculation_rounding_method = "round_globally"
        self.sale_order.action_confirm()
        self.assertTrue(len(self.sale_order.picking_ids))
        for picking in self.sale_order.picking_ids:
            picking.action_assign()
            picking.move_ids.quantity_done = 1
            picking.button_validate()
            self.assertEqual(picking.l10n_ro_amount_untaxed, 100.0)
            self.assertEqual(picking.l10n_ro_amount_tax, 19.0)
            self.assertEqual(picking.l10n_ro_amount_total, 119.0)

    def test_04_lines_distinct_tax(self):
        self.sale_order2.company_id.tax_calculation_rounding_method = "round_globally"
        self.sale_order2.action_confirm()
        self.assertTrue(len(self.sale_order2.picking_ids))
        for picking in self.sale_order2.picking_ids:
            picking.action_assign()
            picking.move_ids.quantity_done = 1
            picking.button_validate()
            self.assertEqual(picking.l10n_ro_amount_untaxed, 200.0)
            self.assertEqual(picking.l10n_ro_amount_tax, 38.0)
            self.assertEqual(picking.l10n_ro_amount_total, 238.0)

    def test_05_distinct_qty(self):
        self.sale_order.action_confirm()
        self.assertTrue(len(self.sale_order.picking_ids))
        for picking in self.sale_order.picking_ids:
            picking.action_assign()
            picking.move_ids.quantity_done = 2.0
            picking.button_validate()
            self.assertEqual(picking.l10n_ro_amount_untaxed, 200.0)
            self.assertEqual(picking.l10n_ro_amount_tax, 38.0)
            self.assertEqual(picking.l10n_ro_amount_total, 238.0)

    def test_06_order_kit(self):
        module_name = "sale_mrp"
        module = (
            self.env["ir.module.module"].sudo().search([("name", "=", module_name)])
        )
        if module.state not in ("installed", "to install", "to upgrade"):
            module.button_immediate_install()

        self.sale_order3.action_confirm()
        self.assertTrue(len(self.sale_order3.picking_ids))
        for picking in self.sale_order3.picking_ids:
            picking.action_assign()
            picking.move_ids.quantity_done = 1.0
            picking.button_validate()

            received = []
            expect = [
                {
                    "l10n_ro_price_tax": 0.32,
                    "l10n_ro_price_unit": 1.6666666666666667,
                    "l10n_ro_price_subtotal": 1.67,
                },
                {
                    "l10n_ro_price_tax": 19.0,
                    "l10n_ro_price_unit": 100.0,
                    "l10n_ro_price_subtotal": 100.0,
                },
            ]
            for move_line in picking.move_line_ids:
                move_line._compute_l10n_ro_valued_fields()
                received.append(
                    {
                        "l10n_ro_price_tax": move_line.l10n_ro_price_tax,
                        "l10n_ro_price_unit": move_line.l10n_ro_price_unit,
                        "l10n_ro_price_subtotal": move_line.l10n_ro_price_subtotal,
                    }
                )

            self.assertListEqual(received, expect)
            self.assertEqual(picking.l10n_ro_amount_tax, 19.32)
