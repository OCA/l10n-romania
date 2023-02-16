# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields
from odoo.tests import Form, tagged

from .common import TestStockPickingValued


@tagged("post_install", "-at_install")
class TestPurchaseStockPickingValued(TestStockPickingValued):
    def _get_agg_lines_key(self, move_line):
        name = move_line.product_id.display_name
        description = move_line.move_id.description_picking
        if description == name or description == move_line.product_id.name:
            description = False
        uom = move_line.product_uom_id
        line_key = (
            str(move_line.product_id.id)
            + "_"
            + name
            + (description or "")
            + "uom "
            + str(uom.id)
        )

        return line_key

    def test_01_confirm_order(self):
        self.purchase_order.button_confirm()
        self.assertTrue(len(self.purchase_order.picking_ids))
        for picking in self.purchase_order.picking_ids:
            picking.action_assign()
            self.assertEqual(picking.l10n_ro_amount_untaxed, 0.0)
            self.assertEqual(picking.l10n_ro_amount_tax, 0.0)
            self.assertEqual(picking.l10n_ro_amount_total, 0.0)

    def test_02_confirm_order(self):
        """Valued picking isn't computed if not reserved"""
        self.purchase_order.button_confirm()
        for picking in self.purchase_order.picking_ids:
            picking.action_assign()
            picking.do_unreserve()
            self.assertEqual(picking.l10n_ro_amount_untaxed, 0.0)
            self.assertEqual(picking.l10n_ro_amount_tax, 0.0)
            self.assertEqual(picking.l10n_ro_amount_total, 0.0)

    def test_03_tax_rounding_method(self):
        self.purchase_order.company_id.tax_calculation_rounding_method = (
            "round_globally"
        )
        self.purchase_order.button_confirm()
        self.assertTrue(len(self.purchase_order.picking_ids))
        for picking in self.purchase_order.picking_ids:
            action = picking.button_validate()
            wizard = Form(
                self.env[action["res_model"]].with_context(action["context"])
            ).save()
            wizard.process()
            self.assertEqual(picking.l10n_ro_amount_untaxed, 100.0)
            self.assertEqual(picking.l10n_ro_amount_tax, 19.0)
            self.assertEqual(picking.l10n_ro_amount_total, 119.0)

    def test_04_lines_distinct_tax(self):
        self.purchase_order2.company_id.tax_calculation_rounding_method = (
            "round_globally"
        )
        self.purchase_order2.button_confirm()
        self.assertTrue(len(self.purchase_order2.picking_ids))
        for picking in self.purchase_order2.picking_ids:
            picking.action_assign()
            picking.move_line_ids.qty_done = 3.0
            picking.button_validate()
            picking._action_done()
            self.assertEqual(picking.l10n_ro_amount_untaxed, 600.0)
            self.assertEqual(picking.l10n_ro_amount_tax, 114.0)
            self.assertEqual(picking.l10n_ro_amount_total, 714.0)

    def test_05_distinct_qty(self):
        self.purchase_order.button_confirm()
        self.assertTrue(len(self.purchase_order.picking_ids))
        for picking in self.purchase_order.picking_ids:
            picking.action_assign()
            picking.move_line_ids.qty_done = 2.0
            picking.button_validate()
            picking._action_done()
            self.assertEqual(picking.l10n_ro_amount_untaxed, 200.0)
            self.assertEqual(picking.l10n_ro_amount_tax, 38.0)
            self.assertEqual(picking.l10n_ro_amount_total, 238.0)

    def test_06_po_currency_qty(self):
        self.env["res.currency.rate"].create(
            {
                "currency_id": self.env.ref("base.EUR").id,
                "name": fields.date.today(),
                "rate": 2.0,
            }
        )
        self.purchase_order.currency_id = self.env.ref("base.EUR")
        self.purchase_order.button_confirm()
        self.assertTrue(len(self.purchase_order.picking_ids))
        for picking in self.purchase_order.picking_ids:
            picking.action_assign()
            picking.move_line_ids.qty_done = 2.0
            picking.button_validate()
            picking._action_done()
            self.assertEqual(picking.l10n_ro_amount_untaxed, 100.0)
            self.assertEqual(picking.l10n_ro_amount_tax, 19.0)
            self.assertEqual(picking.l10n_ro_amount_total, 119.0)

        move_line = self.purchase_order.picking_ids.move_line_ids
        agg_lines = move_line._get_aggregated_product_quantities()
        line_key = self._get_agg_lines_key(move_line)
        exp = {
            "%s"
            % line_key: {
                "name": move_line.product_id.name,
                "description": False,
                "qty_done": 2.0,
                "product_uom": move_line.product_id.uom_id.name,
                "product_uom_rec": move_line.product_id.uom_id,
                "product": move_line.product_id,
                "currency": move_line.company_id.currency_id.id,
                "l10n_ro_price_unit": 50.0,
                "l10n_ro_additional_charges": 0.0,
                "l10n_ro_price_subtotal": 100.0,
                "l10n_ro_price_tax": 19.0,
                "l10n_ro_price_total": 119.0,
                "l10n_ro_currency_id": move_line.company_id.currency_id.id,
            }
        }
        self.assertEqual(agg_lines, exp)

    def test_07_move_line_additional_charges(self):
        self.product_1.purchase_method = "purchase"
        self.product_1.invoice_policy = "order"

        self.purchase_order.button_confirm()

        # proceseaza picking
        picking = self.purchase_order.picking_ids
        picking.action_assign()
        picking.move_line_ids.qty_done = 1.0
        picking.button_validate()
        picking._action_done()

        # adauga LC in factura
        self.purchase_order.action_create_invoice()
        invoice = self.purchase_order.invoice_ids
        invoice.invoice_date = self.purchase_order.date_approve
        invoice_form = Form(invoice)
        with invoice_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.landed_cost
            line_form.quantity = 1
            line_form.price_unit = 10
        invoice = invoice_form.save()
        invoice.action_post()

        self.create_lc(self.purchase_order.picking_ids, 10, 0, vendor_bill=invoice)

        # creaza LC in factura separata si valideaza
        invoice_lc2_form = Form(
            self.env["account.move"].with_context(
                default_move_type="in_invoice",
                account_predictive_bills_disable_prediction=True,
            )
        )
        invoice_lc2_form.invoice_date = self.purchase_order.date_approve
        invoice_lc2_form.date = self.purchase_order.date_approve
        invoice_lc2_form.partner_id = self.purchase_order.partner_id
        with invoice_lc2_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.landed_cost
            line_form.quantity = 1
            line_form.price_unit = 20
        invoice_lc2 = invoice_lc2_form.save()
        invoice_lc2.action_post()
        self.create_lc(self.purchase_order.picking_ids, 20, 0, vendor_bill=invoice_lc2)

        # verifica valori price_unit si additional_charges
        move_line = self.purchase_order.picking_ids.move_line_ids
        agg_lines = move_line._get_aggregated_product_quantities()

        line_key = self._get_agg_lines_key(move_line)
        self.assertEqual(agg_lines[line_key]["l10n_ro_price_unit"], 110.0)
        self.assertEqual(agg_lines[line_key]["l10n_ro_additional_charges"], 20.0)
