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

    def test_posted_document_is_final(self):
        """A posted Proces Verbal is not reset, not cancelled, not deleted.

        It wrote the shelf prices, posted an entry and moved what the stock
        carries. Undoing it in place left the three out of step with each
        other; a document whose entry had been reversed could even be reset
        and posted again, doubling the revaluation. A price decision that
        turned out wrong is revoked by posting another document.
        """
        doc, _line = self._do_price_change(
            self.warehouse_mag1, self.product_retail, 10, 178.5
        )
        self.assertFalse(
            hasattr(doc, "action_draft"),
            "There is no way back from a posted document",
        )
        with self.assertRaises(UserError):
            doc.action_cancel()
        with self.assertRaises(UserError):
            doc.unlink()
        self.assertEqual(doc.state, "done")

    def test_draft_document_can_be_cancelled_and_deleted(self):
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        doc = self.env["l10n.ro.retail.price.change"].create(
            {"warehouse_id": self.warehouse_mag1.id}
        )
        doc.action_load_products()
        doc.action_cancel()
        self.assertEqual(doc.state, "cancel")
        doc.unlink()

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

    # -------------------------------------------------------------------
    # The old side is what holds at posting, not what held at loading
    # -------------------------------------------------------------------
    def test_two_documents_posted_in_series_do_not_double_the_delta(self):
        """Two drafts raised before either is posted.

        The old side used to be frozen when the line was loaded, so the second
        document measured its delta against the markup that was carried before
        the first one moved it - and 378 ended up holding the two deltas added
        together, with nothing in either entry to show the overlap.
        """
        Ledger = self.env["l10n.ro.retail.markup.line"]
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        Doc = self.env["l10n.ro.retail.price.change"]

        def _draft(new_price):
            doc = Doc.create({"warehouse_id": self.warehouse_mag1.id})
            doc.action_load_products()
            doc.line_ids.filtered(
                lambda ln: ln.product_id == self.product_retail
            ).new_price_with_vat = new_price
            return doc

        first = _draft(178.5)  # 150 net: markup 100, VAT 28.50 a unit
        second = _draft(238.0)  # 200 net: markup 150, VAT 38 a unit

        first.action_post()
        second.action_post()

        markup, vat = Ledger._l10n_ro_carried(
            self.warehouse_mag1, self.product_retail, self.env.company
        )
        # Ten units at the last price posted, and only that.
        self.assertAlmostEqual(markup, 10 * 150.0, places=2)
        self.assertAlmostEqual(vat, 10 * 38.0, places=2)
        # The second document measured itself against what the first left.
        self.assertAlmostEqual(second.line_ids.old_markup_unit, 100.0, places=2)
        self.assertAlmostEqual(second.line_ids.markup_diff_total, 500.0, places=2)

    def test_quantity_is_re_read_at_posting(self):
        """A draft loaded yesterday revalues what is on the shelf today."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        doc = self.env["l10n.ro.retail.price.change"].create(
            {"warehouse_id": self.warehouse_mag1.id}
        )
        doc.action_load_products()
        line = doc.line_ids
        self.assertAlmostEqual(line.quantity, 10.0, places=2)
        line.new_price_with_vat = 178.5

        self._do_sale_delivery(self.warehouse_mag1, self.product_retail, 4, 119.0)

        doc.action_post()
        self.assertAlmostEqual(line.quantity, 6.0, places=2)
        # Six units revalued from a markup of 50 to one of 100.
        self.assertAlmostEqual(line.markup_diff_total, 6 * 50.0, places=2)

    # -------------------------------------------------------------------
    # The rate and the quantity it is applied to have to be the same one
    # -------------------------------------------------------------------
    def test_posting_refused_when_the_ledger_does_not_cover_the_stock(self):
        """Stock the ledger never saw makes the rate meaningless.

        The old markup per unit is the ledger balance over the ledger
        quantity, and it is applied to the quantity on the lines. Applying it
        to a larger quantity moves 378 by an amount the rate was never meant
        to produce and leaves the release rate wrong for good.
        """
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        # Stock on the shelf that the ledger knows nothing about - what a shop
        # looks like the day this module is installed on top of live stock,
        # and the position the retail opening balance wizard exists to settle.
        self.env["l10n.ro.retail.markup.line"].sudo().search(
            [("product_id", "=", self.product_retail.id)]
        ).unlink()

        doc = self.env["l10n.ro.retail.price.change"].create(
            {"warehouse_id": self.warehouse_mag1.id}
        )
        doc.action_load_products()
        doc.line_ids.new_price_with_vat = 178.5
        with self.assertRaises(UserError):
            doc.action_post()
        self.assertEqual(doc.state, "draft")

    def test_posting_refused_when_the_document_covers_part_of_the_stock(self):
        """A whole-shop rate must not be applied to a slice of the shop.

        The markup carried is held per warehouse, so the rate a line uses is
        the shop's. A document that drops the line of one shelf still applies
        that rate, to less stock than it was derived from.
        """
        shelf = self.env["stock.location"].create(
            {
                "name": "Raft 2",
                "usage": "internal",
                "location_id": self.loc_mag1.id,
            }
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        self._set_initial_stock(shelf, self.product_retail, 5)
        doc = self.env["l10n.ro.retail.price.change"].create(
            {"warehouse_id": self.warehouse_mag1.id}
        )
        doc.action_load_products()
        self.assertEqual(len(doc.line_ids), 2)
        doc.line_ids.new_price_with_vat = 178.5
        doc.line_ids.filtered(lambda ln: ln.location_id == shelf).unlink()
        with self.assertRaises(UserError):
            doc.action_post()
        self.assertEqual(doc.state, "draft")

    # -------------------------------------------------------------------
    # Cost, taxes, numbering
    # -------------------------------------------------------------------
    def test_cost_of_unrecorded_stock_comes_from_the_quants(self):
        """With nothing in the ledger the cost is the value of the goods.

        ``standard_price`` is a different number on any product not valued at
        standard, and the difference went straight into the markup - the
        retail opening balance wizard settles the same stock against the quant
        value, and the two had to agree.
        """
        product = self.env["product.product"].create(
            {
                "name": "Produs FIFO magazin",
                "is_storable": True,
                "categ_id": self.category_marfa_fifo.id,
                "list_price": 119.0,
                "standard_price": 20.0,
                "taxes_id": [(6, 0, self.tax_19.ids)],
            }
        )
        # Bought at 60 and sitting on the shelf at 60, while the product still
        # quotes 20: on FIFO the two are simply different numbers.
        self._do_purchase_receipt(self.warehouse_mag1, product, 5, 60.0)
        self.env["l10n.ro.retail.markup.line"].sudo().search(
            [("product_id", "=", product.id)]
        ).unlink()

        doc = self.env["l10n.ro.retail.price.change"].create(
            {"warehouse_id": self.warehouse_mag1.id}
        )
        doc.action_load_products()
        line = doc.line_ids.filtered(lambda ln: ln.product_id == product)
        quants = self.env["stock.quant"].search(
            [("product_id", "=", product.id), ("location_id", "=", self.loc_mag1.id)]
        )
        self.assertAlmostEqual(
            line.cost_unit,
            sum(quants.mapped("value")) / sum(quants.mapped("quantity")),
            places=2,
        )
        self.assertNotAlmostEqual(line.cost_unit, 20.0, places=2)

    def test_split_follows_the_warehouse_fiscal_position(self):
        """The VAT the document moves onto 4428 is the one the shop collects,
        so the shelf price is split with the taxes its fiscal position maps
        to - the same ones a stock move is valued with."""
        fiscal_position = self.env["account.fiscal.position"].create(
            {"name": "Retail MAG1", "company_id": self.env.company.id}
        )
        self.env["account.tax"].create(
            {
                "name": "TVA 9% retail",
                "amount_type": "percent",
                "amount": 9.0,
                "type_tax_use": "sale",
                "company_id": self.env.company.id,
                "fiscal_position_ids": [(6, 0, fiscal_position.ids)],
                "original_tax_ids": [(6, 0, self.tax_19.ids)],
            }
        )
        self.warehouse_mag1.l10n_ro_fiscal_position_id = fiscal_position
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        doc = self.env["l10n.ro.retail.price.change"].create(
            {"warehouse_id": self.warehouse_mag1.id}
        )
        doc.action_load_products()
        line = doc.line_ids
        line.new_price_with_vat = 218.0  # 200 net plus 9% VAT
        self.assertAlmostEqual(line.new_vat_unit, 18.0, places=2)

    def test_deleting_a_pricelist_rule_raises_a_document(self):
        """Removing a rule changes the label as surely as editing it."""
        item = (
            self.env["product.pricelist.item"]
            .with_context(skip_retail_price_change=True)
            .create(
                {
                    "pricelist_id": self.pricelist_mag1.id,
                    "applied_on": "0_product_variant",
                    "product_id": self.product_retail.id,
                    "compute_price": "fixed",
                    "fixed_price": 200.0,
                }
            )
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        docs_before = self.env["l10n.ro.retail.price.change"].search([])
        self.env["product.pricelist.item"].browse(item.id).unlink()
        doc = self.env["l10n.ro.retail.price.change"].search([]) - docs_before
        self.assertTrue(doc, "Deleting the rule raised no price change document")
        self.assertEqual(doc.state, "draft")
        # Back to the global rule, which prices at the product's own PVA.
        self.assertAlmostEqual(doc.line_ids.new_price_with_vat, 119.0, places=2)

    def test_each_company_numbers_its_own_documents(self):
        """A shared series gives neither firm a numbering of its own."""
        Sequence = self.env["ir.sequence"]
        other = self.env["res.company"].create({"name": "A doua firma retail"})
        self.assertTrue(
            Sequence.search(
                [
                    ("code", "=", "l10n.ro.retail.price.change"),
                    ("company_id", "=", other.id),
                ]
            ),
            "A new company got no Proces Verbal sequence",
        )
        self.assertFalse(
            Sequence.search(
                [
                    ("code", "=", "l10n.ro.retail.price.change"),
                    ("company_id", "=", False),
                ]
            ),
            "A shared sequence would number both companies out of one series",
        )
        own = Sequence.search(
            [
                ("code", "=", "l10n.ro.retail.price.change"),
                ("company_id", "=", self.env.company.id),
            ]
        )
        self.assertTrue(own)
        # The document takes the series of its own company, not of the one
        # the user happens to be working in.
        doc = self.env["l10n.ro.retail.price.change"].create(
            {"warehouse_id": self.warehouse_mag1.id}
        )
        self.assertTrue(doc.name.startswith("PVSP/"))
