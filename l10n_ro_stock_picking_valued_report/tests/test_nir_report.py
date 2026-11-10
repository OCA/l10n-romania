# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

"""Romanian goods receipt note (NIR) printed inside the shared delivery slip."""

import logging

from odoo.tests import tagged

from .common import TestStockPickingValued

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestNirReport(TestStockPickingValued):
    @classmethod
    @TestStockPickingValued.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        # A NIR is always rendered in Romanian, which requires the language to
        # be installed.
        cls.env["res.lang"]._activate_lang("ro_RO")
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.uom_pack5 = cls.env["uom.uom"].create(
            {
                "name": "Pack of 5",
                "relative_uom_id": cls.uom_unit.id,
                "relative_factor": 5.0,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Toscanello receipt",
                "is_storable": True,
                "categ_id": cls.category_marfa_fifo.id,
                "purchase_method": "receive",
                "uom_id": cls.uom_unit.id,
                "uom_ids": [(6, 0, [cls.uom_pack5.id])],
                "weight": 0.1,
            }
        )
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.warehouse = cls.location.warehouse_id

    def _receive(self, qty, unit_price, packaging_uom=None):
        self.product.standard_price = unit_price
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.in_type_id.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.location.id,
            }
        )
        move_vals = {
            "picking_id": picking.id,
            "product_id": self.product.id,
            "product_uom": self.uom_unit.id,
            "product_uom_qty": qty,
            "location_id": self.supplier_location.id,
            "location_dest_id": self.location.id,
        }
        if packaging_uom:
            move_vals["packaging_uom_id"] = packaging_uom.id
        self.env["stock.move"].create(move_vals)
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move._set_quantity_done(qty)
            move.picked = True
        picking.button_validate()
        return picking

    def test_nir_flags_and_number(self):
        picking = self._receive(100, 2.0)
        self.assertTrue(picking.l10n_ro_is_nir)
        # The NIR is identified by the picking name; no separate number.
        self.assertTrue(picking.name)
        # No supplier set on the manual receipt -> treated as internal.
        self.assertEqual(picking.l10n_ro_supplier_type, "intern")

    def test_nir_supplier_type(self):
        italy = self.env.ref("base.it")
        usa = self.env.ref("base.us")
        ue_supplier = self.env["res.partner"].create(
            {"name": "Sigaro Toscano", "country_id": italy.id}
        )
        import_supplier = self.env["res.partner"].create(
            {"name": "Ashton", "country_id": usa.id}
        )
        picking = self._receive(10, 1.0)
        picking.partner_id = ue_supplier
        self.assertEqual(picking.l10n_ro_supplier_type, "ue")
        picking.partner_id = import_supplier
        self.assertEqual(picking.l10n_ro_supplier_type, "import")

    def test_nir_report_lines_and_packages(self):
        picking = self._receive(100, 2.0, packaging_uom=self.uom_pack5)
        lines = picking._l10n_ro_nir_report_lines()
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertEqual(line["position"], 1)
        self.assertAlmostEqual(line["quantity"], 100.0)
        self.assertAlmostEqual(line["purchase_value"], 200.0, places=2)
        # Subtotal = purchase value + additional charges (net, excl. VAT).
        self.assertAlmostEqual(
            line["subtotal"],
            line["purchase_value"] + line["additional_charges"],
            places=2,
        )
        # Total = subtotal + VAT.
        self.assertAlmostEqual(line["total"], line["subtotal"] + line["tax"], places=2)
        # 100 units in packs of 5 -> 20 packages.
        self.assertAlmostEqual(line["packages"], 20.0, places=2)
        self.assertAlmostEqual(line["weight"], 10.0, places=2)

    def test_nir_renders_in_shared_slip(self):
        """The NIR prints through the shared delivery slip, with a single
        clean title and the twelve-column table."""
        picking = self._receive(100, 2.0, packaging_uom=self.uom_pack5)
        report = self.env["ir.actions.report"]._render_qweb_html(
            "stock.report_deliveryslip", picking.ids
        )
        html = report[0].decode() if isinstance(report[0], bytes) else report[0]
        # Single NIR title (source terms; the test DB renders in English).
        self.assertIn("Goods Receipt Note", html)
        self.assertEqual(
            html.count("Goods Receipt Note"),
            1,
            "The NIR title must appear exactly once (no double title)",
        )
        self.assertIn(picking.name, html)
        # The NIR table and its columns.
        self.assertIn("l10n_ro_nir_table", html)
        self.assertIn("Purchase Value", html)
        self.assertIn("Additional Charges", html)
        self.assertIn("TOTAL NIR", html)
        # The delivery-style order/date/operator block is suppressed.
        self.assertNotIn("Operator:", html)

    def test_nir_forces_romanian(self):
        picking = self._receive(10, 1.0)
        Report = self.env["ir.actions.report"]
        slip_env = Report._l10n_ro_picking_report_env("stock.report_deliveryslip")
        self.assertEqual(picking.with_env(slip_env.env)._get_report_lang(), "ro_RO")
