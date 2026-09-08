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
        # The ledger row a price change document writes: the markup and the
        # deferred VAT move, no goods and no cost do. Written here rather than
        # by posting a document, because this module does not depend on the
        # one that raises them - and a test that quietly did was a test that
        # passed or failed depending on what else was installed.
        self.env["l10n.ro.retail.markup.line"].sudo().create(
            {
                "company_id": self.env.company.id,
                "product_id": self.product_retail.id,
                "location_id": self.loc_mag1.id,
                "quantity": 0.0,
                "cost": 0.0,
                "markup": 500.0,
                "vat": 95.0,
                "origin_type": "price_change",
            }
        )
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
        self.assertEqual(action["context"]["l10n_ro_retail_date_from"], "2026-01-01")
        self.assertEqual(action["context"]["l10n_ro_retail_date_to"], "2026-12-31")
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

    # -------------------------------------------------------------------
    # The period is read as an accounting period, dates and all
    # -------------------------------------------------------------------
    def _over(self, date_from, date_to, warehouse, product):
        return (
            self.env["l10n.ro.stock.retail.report"]
            .with_context(
                l10n_ro_retail_date_from=fields.Date.to_string(date_from),
                l10n_ro_retail_date_to=fields.Date.to_string(date_to),
            )
            .search(
                [
                    ("warehouse_id", "=", warehouse.id),
                    ("product_id", "=", product.id),
                ]
            )
        )

    def test_the_last_day_of_the_period_is_inside_it(self):
        """A row dated on the closing day belongs to the period.

        The bounds used to be timestamps built from the user's local dates as
        if they were UTC, so a shop trading in the evening had its last
        movements counted in the previous day and the closing balance parted
        company with the trial balance at every month end.
        """
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        ledger = (
            self.env["l10n.ro.retail.markup.line"]
            .sudo()
            .search([("product_id", "=", self.product_retail.id)], limit=1)
        )
        day = fields.Date.context_today(self)
        ledger.date = day

        inside = self._over(day, day, self.warehouse_mag1, self.product_retail)
        self.assertAlmostEqual(inside.quantity_in, 10.0, places=2)
        self.assertAlmostEqual(inside.quantity_initial, 0.0, places=2)

        # The row number is the same in both periods, so the values read for
        # the first one are still in the cache when the second is asked for.
        self.env.invalidate_all()
        after = self._over(
            day + timedelta(days=1),
            day + timedelta(days=2),
            self.warehouse_mag1,
            self.product_retail,
        )
        self.assertAlmostEqual(after.quantity_initial, 10.0, places=2)
        self.assertAlmostEqual(after.quantity_in, 0.0, places=2)

    def test_unrecorded_is_silent_over_a_period(self):
        """The quants keep no history, so over a period the column has no
        answer - and reporting the whole recorded quantity as missing, in red,
        made the "Not in the ledger" filter match every row."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        day = fields.Date.context_today(self)
        row = self._over(
            day - timedelta(days=30), day, self.warehouse_mag1, self.product_retail
        )
        self.assertAlmostEqual(row.quantity, 10.0, places=2)
        self.assertAlmostEqual(row.quantity_unrecorded, 0.0, places=2)
        self.assertFalse(
            row.filtered(lambda r: r.quantity_unrecorded != 0),
            "Over a period nothing is unrecorded, because nothing is compared",
        )

    def test_quantities_of_a_period_add_up(self):
        """Opening plus in plus out plus corrections is the closing balance.

        The opening balance recognises stock the ledger had never seen, and it
        moves no goods, so its quantity belonged in none of the movement
        buckets. Left out of the report altogether it simply went missing from
        the arithmetic of the period.
        """
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        self.env["l10n.ro.retail.markup.line"].sudo().search(
            [("product_id", "=", self.product_retail.id)]
        ).unlink()
        wizard = self.env["l10n.ro.retail.opening.balance"].create(
            {"warehouse_ids": [(6, 0, self.warehouse_mag1.ids)]}
        )
        wizard.action_refresh()
        wizard.action_post()

        day = fields.Date.context_today(self)
        row = self._over(
            day - timedelta(days=1), day, self.warehouse_mag1, self.product_retail
        )
        self.assertAlmostEqual(row.quantity_adjustment, 10.0, places=2)
        self.assertAlmostEqual(
            row.quantity_initial
            + row.quantity_in
            + row.quantity_out
            + row.quantity_adjustment,
            row.quantity,
            places=2,
        )

    # -------------------------------------------------------------------
    # The rows that most need to be seen
    # -------------------------------------------------------------------
    def test_a_negative_quantity_keeps_its_row(self):
        """Sold past the stock: nothing on the shelf, a balance still on 378.

        Testing the quantity alone dropped exactly this row - the one case a
        reconciliation against the trial balance exists to catch.
        """
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        self.env["l10n.ro.retail.markup.line"].sudo().create(
            {
                "company_id": self.env.company.id,
                "product_id": self.product_retail.id,
                "location_id": self.loc_mag1.id,
                "quantity": -14.0,
                "cost": -700.0,
                "markup": -640.0,
                "vat": -190.0,
                "origin_type": "manual",
            }
        )
        self.env["stock.quant"].sudo().search(
            [
                ("product_id", "=", self.product_retail.id),
                ("location_id", "=", self.loc_mag1.id),
            ]
        ).unlink()

        row = self._report_line(self.warehouse_mag1, self.product_retail)
        self.assertEqual(len(row), 1, "A row with a stranded balance vanished")
        self.assertAlmostEqual(row.quantity, -4.0, places=2)
        self.assertAlmostEqual(row.markup_total, -140.0, places=2)

    def test_a_product_without_a_shelf_price_does_not_break_the_report(self):
        """The retail module refuses to guess a shelf price, so asking for one
        that is not configured raises. A report that raises on one unpriced
        article shows nothing at all - and unpriced articles on the shelf are
        what the reader is here to find."""
        self.env["product.pricelist.item"].search(
            [("pricelist_id", "=", self.pricelist_mag1.id)]
        ).with_context(skip_retail_price_change=True).unlink()
        self.env["l10n.ro.retail.markup.line"].sudo().create(
            {
                "company_id": self.env.company.id,
                "product_id": self.product_retail.id,
                "location_id": self.loc_mag1.id,
                "quantity": 5.0,
                "cost": 250.0,
                "markup": 250.0,
                "vat": 95.0,
                "origin_type": "manual",
            }
        )
        row = self._report_line(self.warehouse_mag1, self.product_retail)
        self.assertAlmostEqual(row.retail_value, 595.0, places=2)
        self.assertAlmostEqual(row.current_price_unit, 0.0, places=2)

    def test_the_report_is_filtered_by_company(self):
        """A model on a SQL view gets no multi-company filtering of its own,
        and the menu carries no domain: without a record rule every shop of
        every company was readable."""
        other = self.env["res.company"].create({"name": "Alta firma retail"})
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        rows = (
            self.env["l10n.ro.stock.retail.report"]
            .with_context(allowed_company_ids=[other.id])
            .with_company(other)
            .search([("product_id", "=", self.product_retail.id)])
        )
        self.assertFalse(rows, "Another company's shop was readable")
        rows = self.env["l10n.ro.stock.retail.report"].search(
            [("product_id", "=", self.product_retail.id)]
        )
        self.assertTrue(rows)
