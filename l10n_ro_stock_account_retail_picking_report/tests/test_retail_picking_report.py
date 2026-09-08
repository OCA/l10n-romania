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

    def test_a_row_bought_by_the_dozen_prints_its_whole_cost(self):
        """Goods bought in dozens and stocked in units.

        The share of the move a printed row takes used to divide a quantity
        counted in the line's unit by the demand in the product's, so this row
        printed a twelfth of the cost, the markup and the shelf price - on the
        document the shop signs when the goods arrive.
        """
        product = self.env["product.product"].create(
            {
                "name": "Marfa la duzina",
                "is_storable": True,
                "categ_id": self.product_retail.categ_id.id,
                "list_price": 119.0,
                "standard_price": 50.0,
                "taxes_id": [(6, 0, self.tax_19.ids)],
            }
        )
        dozen = self.env.ref("uom.product_uom_dozen")
        move = self.env["stock.move"].create(
            {
                "company_id": self.env.company.id,
                "product_id": product.id,
                "product_uom": dozen.id,
                "product_uom_qty": 2,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.loc_mag1.id,
                "picking_type_id": self.warehouse_mag1.in_type_id.id,
            }
        )
        move._action_confirm()
        move._action_assign()
        move._set_quantity_done(2)
        move.picked = True
        move._action_done()
        picking = move.picking_id
        # The line counts dozens, the move counts units: exactly the mismatch.
        self.assertEqual(move.move_line_ids.product_uom_id, dozen)
        self.assertAlmostEqual(move.move_line_ids.quantity, 2.0, places=2)
        self.assertAlmostEqual(move.product_qty, 24.0, places=2)

        rows = picking.move_line_ids._get_aggregated_product_quantities()
        row = next(iter(rows.values()))
        # Twenty-four units at a cost of 50 and a shelf price of 119.
        self.assertAlmostEqual(row["l10n_ro_retail_cost_subtotal"], 1200.0, places=2)
        self.assertAlmostEqual(row["l10n_ro_retail_markup"], 1200.0, places=2)
        self.assertAlmostEqual(row["l10n_ro_retail_vat"], 456.0, places=2)
        self.assertAlmostEqual(row["l10n_ro_retail_price_total"], 2856.0, places=2)

    def test_an_over_reception_prints_what_arrived(self):
        """Twelve received against an order for ten.

        No backorder is created, so the demand stays at ten while twelve were
        valued: dividing by the demand printed a fifth more than went on 371.
        """
        _po, move = self._do_purchase_receipt(
            self.warehouse_mag1, self.product_retail, 10, 50.0, qty_done=12
        )
        rows = move.picking_id.move_line_ids._get_aggregated_product_quantities()
        row = next(iter(rows.values()))
        self.assertAlmostEqual(row["l10n_ro_retail_cost_subtotal"], 600.0, places=2)
        self.assertAlmostEqual(row["l10n_ro_retail_markup"], 600.0, places=2)
        self.assertAlmostEqual(row["l10n_ro_retail_price_total"], 1428.0, places=2)

    def test_marking_a_warehouse_retail_updates_older_transfers(self):
        """A shop is routinely marked retail after it has been trading.

        The flag depended on the locations of the moves and not on what those
        locations are, so every transfer made before that day went on printing
        without its reception note title.
        """
        self._set_initial_stock(self.location, self.product_retail, 10)
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Magazin nou", "code": "MAGN"}
        )
        move = self._do_transfer(
            self.location, warehouse.lot_stock_id, self.product_retail, 4
        )
        self.assertFalse(move.picking_id.l10n_ro_retail_incoming)

        warehouse.l10n_ro_retail = True
        self.assertTrue(
            move.picking_id.l10n_ro_retail_incoming,
            "The transfer still prints without its reception note title",
        )
