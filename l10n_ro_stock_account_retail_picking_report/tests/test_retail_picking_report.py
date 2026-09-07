# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account_retail.tests.common import TestRetailCommon


@tagged("post_install", "-at_install")
class TestRetailPickingReport(TestRetailCommon):
    def test_reception_note_shows_cost_markup_and_shelf_price(self):
        """The note prints what was loaded, not a recomputation.

        Cost 50 a unit, shelf price 119 VAT included: 100 net, so a markup of
        50 (100%) and 19 of deferred VAT a unit.
        """
        self._set_initial_stock(self.location, self.product_retail, 10)
        move = self._do_transfer(self.location, self.loc_mag1, self.product_retail, 4)
        picking = move.picking_id
        self.assertTrue(picking.l10n_ro_retail_incoming)

        rows = picking.move_line_ids._get_aggregated_product_quantities()
        self.assertEqual(len(rows), 1)
        row = next(iter(rows.values()))
        self.assertAlmostEqual(row["l10n_ro_retail_cost_unit"], 50.0, places=2)
        self.assertAlmostEqual(row["l10n_ro_retail_cost_subtotal"], 200.0, places=2)
        self.assertAlmostEqual(row["l10n_ro_retail_markup"], 200.0, places=2)
        self.assertAlmostEqual(row["l10n_ro_retail_markup_percent"], 100.0, places=2)
        self.assertAlmostEqual(row["l10n_ro_retail_price_no_vat_unit"], 100.0, places=2)
        self.assertAlmostEqual(row["l10n_ro_retail_vat"], 76.0, places=2)
        self.assertAlmostEqual(row["l10n_ro_retail_price_unit"], 119.0, places=2)
        self.assertAlmostEqual(row["l10n_ro_retail_price_total"], 476.0, places=2)

    def test_plain_transfer_carries_the_keys_at_zero(self):
        """A transfer that touches no shop still has to answer for the keys:
        the template reads them on every row."""
        shelf = self.env["stock.location"].create(
            {
                "name": "Raft depozit",
                "usage": "internal",
                "location_id": self.location.id,
            }
        )
        self._set_initial_stock(self.location, self.product_retail, 10)
        move = self._do_transfer(self.location, shelf, self.product_retail, 4)
        picking = move.picking_id
        self.assertFalse(picking.l10n_ro_retail_incoming)
        rows = picking.move_line_ids._get_aggregated_product_quantities()
        row = next(iter(rows.values()))
        self.assertEqual(row["l10n_ro_retail_markup"], 0.0)
        self.assertEqual(row["l10n_ro_retail_price_total"], 0.0)

    def test_reception_note_renders(self):
        """Render the note. An xpath that no longer matches its anchor only
        fails here, never at install."""
        self._set_initial_stock(self.location, self.product_retail, 10)
        move = self._do_transfer(self.location, self.loc_mag1, self.product_retail, 4)
        html = self.env["ir.actions.report"]._render_qweb_html(
            "stock.action_report_delivery", move.picking_id.ids
        )[0]
        html = html.decode() if isinstance(html, bytes) else html
        self.assertIn("Goods Receipt and Discrepancy Note", html)
        self.assertIn("Markup %", html)
        self.assertIn("Deferred VAT", html)
