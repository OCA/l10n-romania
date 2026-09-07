# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account_retail.tests.common import (
    TestRetailCommon,
)


@tagged("post_install", "-at_install")
class TestRetailPriceChange(TestRetailCommon):
    def _do_price_change(self, warehouse, product, qty, new_price_with_vat):
        self._set_initial_stock(warehouse.lot_stock_id, product, qty)
        doc = self.env["l10n.ro.retail.price.change"].create(
            {"warehouse_id": warehouse.id}
        )
        doc.action_load_products()
        line = doc.line_ids.filtered(lambda ln: ln.product_id == product)
        self.assertTrue(line, "Price change line was not loaded")
        line.new_price_with_vat = new_price_with_vat
        doc.action_post()
        return doc, line

    def test_price_change_increase_journal_entries(self):
        """Raising a product's retail price at MAG1: the delta is
        positive, so the store's own 371 is debited and its own 378/4428
        credited (more value now sits in stock at the higher price)."""
        doc, line = self._do_price_change(
            self.warehouse_mag1, self.product_retail, 10, 178.5
        )
        self.assertEqual(doc.state, "done")
        move = doc.account_move_id
        self.assertTrue(move, "No account move created for the price change")
        markup_delta = round(line.markup_diff_total, 2)
        vat_delta = round(line.vat_diff_total, 2)
        self.assertGreater(markup_delta, 0)
        self.assertGreater(vat_delta, 0)
        self.assertEqual(
            self._lines_as_tuples(move),
            sorted(
                [
                    (self.account_371_mag1.id, markup_delta, 0.0),
                    (self.account_378_mag1.id, 0.0, markup_delta),
                    (self.account_371_mag1.id, vat_delta, 0.0),
                    (self.account_4428_mag1.id, 0.0, vat_delta),
                ]
            ),
        )

    def test_price_change_decrease_journal_entries(self):
        """Lowering a product's retail price at MAG1: the delta is
        negative, so the sides flip - 378/4428 debited, 371 credited."""
        doc, line = self._do_price_change(
            self.warehouse_mag1, self.product_retail, 10, 59.5
        )
        self.assertEqual(doc.state, "done")
        move = doc.account_move_id
        self.assertTrue(move, "No account move created for the price change")
        self.assertLess(line.markup_diff_total, 0)
        self.assertLess(line.vat_diff_total, 0)
        markup_delta = round(abs(line.markup_diff_total), 2)
        vat_delta = round(abs(line.vat_diff_total), 2)
        self.assertEqual(
            self._lines_as_tuples(move),
            sorted(
                [
                    (self.account_378_mag1.id, markup_delta, 0.0),
                    (self.account_371_mag1.id, 0.0, markup_delta),
                    (self.account_4428_mag1.id, vat_delta, 0.0),
                    (self.account_371_mag1.id, 0.0, vat_delta),
                ]
            ),
        )

    def test_pricelist_item_change_creates_draft_price_change_document(self):
        """Changing MAG1's retail pricelist price for a product that
        already has stock on hand auto-generates a DRAFT Proces Verbal de
        Schimbare Pret - it is NOT auto-posted, someone still has to
        review and post it before any accounting entry is created."""
        item = (
            self.env["product.pricelist.item"]
            .with_context(skip_retail_price_change=True)
            .create(
                {
                    "pricelist_id": self.pricelist_mag1.id,
                    "applied_on": "0_product_variant",
                    "product_id": self.product_retail.id,
                    "compute_price": "fixed",
                    "fixed_price": 100.0,
                }
            )
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        docs_before = self.env["l10n.ro.retail.price.change"].search([])

        # `item` still carries `skip_retail_price_change=True` from its own
        # creation (context sticks to a recordset) - browse a fresh one so
        # this write isn't silently skipped too.
        self.env["product.pricelist.item"].browse(item.id).write({"fixed_price": 130.0})

        doc = self.env["l10n.ro.retail.price.change"].search([]) - docs_before
        self.assertTrue(doc, "No auto price-change document was created")
        self.assertTrue(doc.auto_created)
        self.assertEqual(doc.state, "draft")
        self.assertFalse(doc.account_move_id)
        self.assertEqual(doc.warehouse_id, self.warehouse_mag1)
        self.assertEqual(len(doc.line_ids), 1)
        line = doc.line_ids
        self.assertEqual(line.product_id, self.product_retail)
        self.assertAlmostEqual(line.quantity, 10.0, places=2)
        # A retail pricelist holds the shelf price VAT included, so the rule's
        # own figures are the PVA - no 1.19 conversion on the way in or out.
        self.assertAlmostEqual(line.old_price_with_vat, 100.0, places=2)
        self.assertAlmostEqual(line.new_price_with_vat, 130.0, places=2)

    # -------------------------------------------------------------------
    # The document is the only way to move the markup, and only once
    # -------------------------------------------------------------------
    def test_price_change_moves_the_carried_markup(self):
        """Posting must change what the stock carries, not only post an
        entry: the next sale has to release the new markup."""
        Ledger = self.env["l10n.ro.retail.markup.line"]
        doc, line = self._do_price_change(
            self.warehouse_mag1, self.product_retail, 10, 178.5
        )
        markup, vat = Ledger._l10n_ro_carried(
            self.warehouse_mag1, self.product_retail, self.env.company
        )
        # 10 units at 178.50 incl = 150 net: markup 100 and VAT 28.50 a unit.
        self.assertAlmostEqual(markup, 1000.0, places=2)
        self.assertAlmostEqual(vat, 285.0, places=2)
        self.assertTrue(doc.markup_line_ids)
        self.assertAlmostEqual(
            sum(doc.markup_line_ids.mapped("markup")),
            line.markup_diff_total,
            places=2,
        )

    def test_price_change_writes_pricelist_vat_included(self):
        """The shelf price written back on the pricelist is the PVA itself,
        VAT included - reading it back must give the same number."""
        self._do_price_change(self.warehouse_mag1, self.product_retail, 10, 178.5)
        self.assertAlmostEqual(
            self.product_retail._l10n_ro_get_retail_price(
                warehouse=self.warehouse_mag1
            ),
            178.5,
            places=2,
        )

    def test_action_draft_refused_after_posting(self):
        """A posted document cannot go back to draft and be posted again.

        Checking only for a *posted* entry let a document whose entry had
        been reversed - and so left cancelled - be reset and posted a second
        time, doubling the revaluation.
        """
        doc, _line = self._do_price_change(
            self.warehouse_mag1, self.product_retail, 10, 178.5
        )
        with self.assertRaises(UserError):
            doc.action_draft()
        doc.account_move_id.button_draft()
        doc.account_move_id.button_cancel()
        with self.assertRaises(UserError):
            doc.action_draft()
        self.assertEqual(doc.state, "done")

    def test_proces_verbal_renders(self):
        """The Proces Verbal has to print - it is the document the shop signs."""
        doc, _line = self._do_price_change(
            self.warehouse_mag1, self.product_retail, 10, 178.5
        )
        html = self.env["ir.actions.report"]._render_qweb_html(
            "l10n_ro_stock_account_retail_price_change."
            "action_report_retail_price_change",
            doc.ids,
        )[0]
        html = html.decode() if isinstance(html, bytes) else html
        self.assertIn("Retail Price Change Report", html)
        self.assertIn("Commercial Markup (378)", html)
        self.assertIn("Deferred VAT (4428)", html)
        self.assertIn(doc.name, html)

    def test_document_settles_a_ledger_that_drifted_from_the_shelf_price(self):
        """The document has to be able to put a drifted ledger right.

        Loading it used to put today's shelf price on both sides, so a shop
        whose 371 no longer matched its own price list produced a document
        that posted nothing. The old side now states what the stock carries,
        so loading and posting brings 371, 378 and 4428 to the shelf price.
        """
        self._set_initial_stock(
            self.warehouse_mag1.lot_stock_id, self.product_retail, 10
        )
        # Force a drift of the kind a bad starting position leaves behind:
        # the ledger carries more than the shelf price says it should.
        self.env["l10n.ro.retail.markup.line"].sudo().create(
            {
                "company_id": self.env.company.id,
                "product_id": self.product_retail.id,
                "location_id": self.warehouse_mag1.lot_stock_id.id,
                "quantity": 0.0,
                "cost": 0.0,
                "markup": 100.0,
                "vat": 50.0,
                "origin_type": "manual",
            }
        )
        Ledger = self.env["l10n.ro.retail.markup.line"]
        _qty, cost, markup, vat = Ledger._l10n_ro_balance(
            self.warehouse_mag1, self.product_retail, self.env.company
        )
        self.assertAlmostEqual(cost + markup + vat, 1340.0, places=2)  # 1190 + 150

        doc = self.env["l10n.ro.retail.price.change"].create(
            {"warehouse_id": self.warehouse_mag1.id}
        )
        doc.action_load_products()
        line = doc.line_ids.filtered(lambda ln: ln.product_id == self.product_retail)
        # The old side reports what is carried, the new side the shelf price.
        self.assertAlmostEqual(line.old_price_with_vat, 134.0, places=2)
        self.assertAlmostEqual(line.new_price_with_vat, 119.0, places=2)
        self.assertAlmostEqual(line.markup_diff_total, -100.0, places=2)
        self.assertAlmostEqual(line.vat_diff_total, -50.0, places=2)

        doc.action_post()
        _qty, cost, markup, vat = Ledger._l10n_ro_balance(
            self.warehouse_mag1, self.product_retail, self.env.company
        )
        # Back to 10 units at the shelf price of 119.
        self.assertAlmostEqual(cost + markup + vat, 1190.0, places=2)
        self.assertAlmostEqual(markup, 500.0, places=2)
        self.assertAlmostEqual(vat, 190.0, places=2)
