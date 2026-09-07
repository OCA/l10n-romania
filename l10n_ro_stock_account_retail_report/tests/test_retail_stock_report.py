# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account_retail.tests.common import TestRetailCommon


@tagged("post_install", "-at_install")
class TestRetailStockReport(TestRetailCommon):
    def _report_line(self, warehouse, product):
        return self.env["l10n.ro.stock.retail.report"].search(
            [
                ("warehouse_id", "=", warehouse.id),
                ("product_id", "=", product.id),
            ]
        )

    def test_report_shows_what_371_carries(self):
        """One row per (warehouse, product), split the way 371 is split.

        Ten units at a cost of 50 and a shelf price of 119 VAT included:
        500 of cost, 500 of markup, 190 of deferred VAT, 1190 on 371.
        """
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        row = self._report_line(self.warehouse_mag1, self.product_retail)
        self.assertEqual(len(row), 1)
        self.assertAlmostEqual(row.quantity, 10.0, places=2)
        self.assertAlmostEqual(row.cost_total, 500.0, places=2)
        self.assertAlmostEqual(row.markup_total, 500.0, places=2)
        self.assertAlmostEqual(row.vat_total, 190.0, places=2)
        self.assertAlmostEqual(row.retail_value, 1190.0, places=2)
        self.assertAlmostEqual(row.cost_unit, 50.0, places=2)
        self.assertAlmostEqual(row.retail_price_unit, 119.0, places=2)

    def test_nothing_to_revalue_when_the_price_has_not_moved(self):
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        row = self._report_line(self.warehouse_mag1, self.product_retail)
        self.assertAlmostEqual(row.current_price_unit, 119.0, places=2)
        self.assertAlmostEqual(row.price_gap_total, 0.0, places=2)

    def test_price_moved_without_a_document_shows_up_as_to_revalue(self):
        """The gap column is the point of the report: it names the amount a
        price change document still has to settle."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        self.env["product.pricelist.item"].with_context(
            skip_retail_price_change=True
        ).create(
            {
                "pricelist_id": self.pricelist_mag1.id,
                "applied_on": "0_product_variant",
                "product_id": self.product_retail.id,
                "compute_price": "fixed",
                "fixed_price": 178.5,
            }
        )
        row = self._report_line(self.warehouse_mag1, self.product_retail)
        self.assertAlmostEqual(row.current_price_unit, 178.5, places=2)
        # 10 * 178.50 wanted against 1190 carried
        self.assertAlmostEqual(row.price_gap_total, 595.0, places=2)

    def test_sold_out_products_leave_the_report(self):
        """A product the shop no longer holds carries nothing on 371, so it
        has no line - the view only keeps positive quantities."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 4)
        self._do_sale_delivery(self.warehouse_mag1, self.product_retail, 4, 119.0)
        self.assertFalse(self._report_line(self.warehouse_mag1, self.product_retail))

    def test_each_shop_reports_its_own_stock(self):
        """Two shops holding the same product are two rows, each with the
        markup its own pricelist loaded."""
        self.env["product.pricelist.item"].with_context(
            skip_retail_price_change=True
        ).create(
            {
                "pricelist_id": self.pricelist_mag2.id,
                "applied_on": "0_product_variant",
                "product_id": self.product_retail.id,
                "compute_price": "fixed",
                "fixed_price": 238.0,  # 200 net, so a markup of 150 a unit
            }
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        self._set_initial_stock(self.loc_mag2, self.product_retail, 10)
        row1 = self._report_line(self.warehouse_mag1, self.product_retail)
        row2 = self._report_line(self.warehouse_mag2, self.product_retail)
        self.assertAlmostEqual(row1.markup_total, 500.0, places=2)
        self.assertAlmostEqual(row2.markup_total, 1500.0, places=2)

    # -------------------------------------------------------------------
    # As of a date, and over a period
    # -------------------------------------------------------------------
    def _at(self, days):
        """A datetime string `days` away from the moment the stock moved."""
        return fields.Datetime.to_string(fields.Datetime.now() + timedelta(days=days))

    def test_the_three_columns_add_up_to_371(self):
        """Cost, markup and deferred VAT are the balances of 371, 378 and
        4428 for this stock - that is what makes the report checkable."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        row = self._report_line(self.warehouse_mag1, self.product_retail)
        self.assertAlmostEqual(
            row.cost_total + row.markup_total + row.vat_total,
            row.retail_value,
            places=2,
        )
        self.assertAlmostEqual(row.retail_value, 1190.0, places=2)

    def test_report_as_of_a_date_before_the_stock_arrived(self):
        """Nothing had happened yet, so the shop shows nothing."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        report = self.env["l10n.ro.stock.retail.report"].with_context(
            l10n_ro_retail_date_to=self._at(-1)
        )
        self.assertFalse(
            report.search(
                [
                    ("warehouse_id", "=", self.warehouse_mag1.id),
                    ("product_id", "=", self.product_retail.id),
                ]
            )
        )

    def test_report_over_a_period_splits_opening_movements_and_closing(self):
        """A product received and partly sold inside the period shows the
        movement, not just the leftover."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        self._do_sale_delivery(self.warehouse_mag1, self.product_retail, 4, 119.0)
        report = self.env["l10n.ro.stock.retail.report"].with_context(
            l10n_ro_retail_date_from=self._at(-1),
            l10n_ro_retail_date_to=self._at(1),
        )
        row = report.search(
            [
                ("warehouse_id", "=", self.warehouse_mag1.id),
                ("product_id", "=", self.product_retail.id),
            ]
        )
        self.assertEqual(len(row), 1)
        # Nothing before the period started.
        self.assertAlmostEqual(row.quantity_initial, 0.0, places=2)
        self.assertAlmostEqual(row.retail_initial, 0.0, places=2)
        # Ten in, four out, six left.
        self.assertAlmostEqual(row.quantity_in, 10.0, places=2)
        self.assertAlmostEqual(row.markup_in, 500.0, places=2)
        self.assertAlmostEqual(row.quantity_out, -4.0, places=2)
        self.assertAlmostEqual(row.markup_out, -200.0, places=2)
        self.assertAlmostEqual(row.quantity, 6.0, places=2)
        self.assertAlmostEqual(row.markup_total, 300.0, places=2)
        self.assertAlmostEqual(row.vat_total, 114.0, places=2)
        self.assertAlmostEqual(row.retail_value, 714.0, places=2)  # 6 * 119

    def test_a_product_that_came_and_went_keeps_its_line_over_a_period(self):
        """Sold out by the end, but the period is exactly where you look to
        see that it moved at all."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 4)
        self._do_sale_delivery(self.warehouse_mag1, self.product_retail, 4, 119.0)
        report = self.env["l10n.ro.stock.retail.report"].with_context(
            l10n_ro_retail_date_from=self._at(-1),
            l10n_ro_retail_date_to=self._at(1),
        )
        row = report.search(
            [
                ("warehouse_id", "=", self.warehouse_mag1.id),
                ("product_id", "=", self.product_retail.id),
            ]
        )
        self.assertEqual(len(row), 1)
        self.assertAlmostEqual(row.quantity_in, 4.0, places=2)
        self.assertAlmostEqual(row.quantity_out, -4.0, places=2)
        self.assertAlmostEqual(row.quantity, 0.0, places=2)
        self.assertAlmostEqual(row.retail_value, 0.0, places=2)

    def test_a_price_change_shows_as_a_correction_not_a_movement(self):
        """A revaluation moves no goods: it belongs in the corrections
        column, and it must not disturb the quantities."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        doc = self.env["l10n.ro.retail.price.change"].create(
            {"warehouse_id": self.warehouse_mag1.id}
        )
        doc.action_load_products()
        doc.line_ids.new_price_with_vat = 178.5
        doc.action_post()
        report = self.env["l10n.ro.stock.retail.report"].with_context(
            l10n_ro_retail_date_from=self._at(-1),
            l10n_ro_retail_date_to=self._at(1),
        )
        row = report.search(
            [
                ("warehouse_id", "=", self.warehouse_mag1.id),
                ("product_id", "=", self.product_retail.id),
            ]
        )
        self.assertAlmostEqual(row.quantity, 10.0, places=2)
        self.assertAlmostEqual(row.markup_adjustment, 500.0, places=2)
        self.assertAlmostEqual(row.vat_adjustment, 95.0, places=2)
        self.assertAlmostEqual(row.cost_adjustment, 0.0, places=2)
        self.assertAlmostEqual(row.retail_value, 1785.0, places=2)  # 10 * 178.50

    def test_wizard_opens_the_report_over_its_period(self):
        wizard = self.env["l10n.ro.stock.retail.report.wizard"].create(
            {
                "date_from": "2026-01-01",
                "date_to": "2026-12-31",
                "warehouse_ids": [(6, 0, self.warehouse_mag1.ids)],
            }
        )
        action = wizard.action_open_report()
        self.assertEqual(
            action["context"]["l10n_ro_retail_date_to"], "2026-12-31 23:59:59"
        )
        self.assertIn(("warehouse_id", "in", self.warehouse_mag1.ids), action["domain"])

    # -------------------------------------------------------------------
    # Stock the ledger has never seen
    # -------------------------------------------------------------------
    def test_stock_the_ledger_never_saw_still_shows_up(self):
        """The report must not hide the population that needs attention.

        Built on the ledger alone it showed nothing for a shop that was
        trading before the module arrived - which is precisely where someone
        would look to find out why 378 holds nothing.
        """
        self._set_initial_stock(self.loc_mag1, self.product_retail, 40)
        self.env["l10n.ro.retail.markup.line"].sudo().search(
            [("product_id", "=", self.product_retail.id)]
        ).unlink()

        row = self._report_line(self.warehouse_mag1, self.product_retail)
        self.assertEqual(len(row), 1, "Unrecorded stock vanished from the report")
        self.assertAlmostEqual(row.quantity_on_hand, 40.0, places=2)
        self.assertAlmostEqual(row.quantity, 0.0, places=2)
        self.assertAlmostEqual(row.quantity_unrecorded, 40.0, places=2)
        self.assertAlmostEqual(row.markup_total, 0.0, places=2)

    def test_nothing_unrecorded_once_the_ledger_is_complete(self):
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        row = self._report_line(self.warehouse_mag1, self.product_retail)
        self.assertAlmostEqual(row.quantity_on_hand, 10.0, places=2)
        self.assertAlmostEqual(row.quantity_unrecorded, 0.0, places=2)
