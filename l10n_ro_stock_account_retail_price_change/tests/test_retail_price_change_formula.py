# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account_retail.tests.common import (
    TestRetailCommon,
)


@tagged("post_install", "-at_install")
class TestRetailPriceChangeFormula(TestRetailCommon):
    """A shop that prices its shelves with a rule, not with a price.

    MAG1 already carries a global formula over the sale price, which is how
    the common fixture prices everything. These tests add the other ways a
    shelf price is decided in a real shop - a rule over a category, a markup
    over the buying list, the sale price itself - and check that moving any of
    them raises the Proces Verbal, that posting it does not quietly replace
    the rule with a fixed price, and that the prices which move with nobody
    writing anything are caught by the reconciliation.
    """

    def setUp(self):
        super().setUp()
        self.Document = self.env["l10n.ro.retail.price.change"]
        self.Item = self.env["product.pricelist.item"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _new_item(self, **vals):
        """A rule created without raising a document for its own creation."""
        return self.Item.with_context(skip_retail_price_change=True).create(vals)

    def _edit(self, item, **vals):
        """Write on a rule through a recordset that carries no skip context.

        The context sticks to the recordset a rule was created with, so
        editing the record returned by ``_new_item`` would silently skip the
        hook this whole file is about.
        """
        self.Item.browse(item.id).write(vals)

    def _documents_raised_by(self, action):
        before = self.Document.search([])
        action()
        return self.Document.search([]) - before

    def _line_for(self, document, product):
        return document.line_ids.filtered(lambda ln: ln.product_id == product)

    # ------------------------------------------------------------------
    # A rule over a range moves real shelf labels
    # ------------------------------------------------------------------
    def test_category_rule_change_raises_a_document(self):
        """A price set on a category is the shelf price of everything in it.

        It used to be skipped, on the grounds that a default over a range is
        not a decision about each article underneath. The article on the shelf
        disagrees: its label changed, and 371 did not.
        """
        item = self._new_item(
            pricelist_id=self.pricelist_mag1.id,
            applied_on="2_product_category",
            categ_id=self.product_retail.categ_id.id,
            compute_price="fixed",
            fixed_price=150.0,
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)

        documents = self._documents_raised_by(
            lambda: self._edit(item, fixed_price=180.0)
        )

        self.assertTrue(documents, "A category rule moved no shelf price")
        self.assertEqual(documents.warehouse_id, self.warehouse_mag1)
        line = self._line_for(documents, self.product_retail)
        self.assertTrue(line, "The product under the category is not on the document")
        self.assertAlmostEqual(line.old_price_with_vat, 150.0, places=2)
        self.assertAlmostEqual(line.new_price_with_vat, 180.0, places=2)

    def test_category_rule_only_covers_its_own_category(self):
        """The scope of the rule is the scope of the document.

        A category rule names a range, and the document has to hold the goods
        in that range and nothing else - otherwise following category rules at
        all would mean revaluing the whole shop every time one of them moved.
        """
        other_category = self.env["product.category"].create(
            {
                "name": "Alta categorie retail",
                "parent_id": self.product_retail.categ_id.parent_id.id,
                "property_cost_method": "fifo",
                "property_valuation": "real_time",
            }
        )
        outsider = self.env["product.product"].create(
            {
                "name": "Produs din alta categorie",
                "is_storable": True,
                "categ_id": other_category.id,
                "list_price": 119.0,
                "standard_price": 50.0,
                "taxes_id": [(6, 0, self.tax_19.ids)],
            }
        )
        item = self._new_item(
            pricelist_id=self.pricelist_mag1.id,
            applied_on="2_product_category",
            categ_id=self.product_retail.categ_id.id,
            compute_price="fixed",
            fixed_price=150.0,
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        self._set_initial_stock(self.loc_mag1, outsider, 10)

        documents = self._documents_raised_by(
            lambda: self._edit(item, fixed_price=180.0)
        )

        self.assertTrue(documents)
        self.assertTrue(self._line_for(documents, self.product_retail))
        self.assertFalse(
            self._line_for(documents, outsider),
            "A product outside the category was revalued by a rule that never "
            "priced it",
        )

    def test_formula_markup_change_raises_a_document(self):
        """The shop that prices at a markup changes its prices in the formula.

        Nothing about the fixed price of any article is written; the term of
        the formula is. Watching only ``fixed_price`` saw none of it.
        """
        item = self._new_item(
            pricelist_id=self.pricelist_mag1.id,
            applied_on="0_product_variant",
            product_id=self.product_retail.id,
            compute_price="formula",
            base="list_price",
            price_discount=0.0,
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)

        # A negative discount is a mark-up: 119 becomes 119 * 1.20.
        documents = self._documents_raised_by(
            lambda: self._edit(item, price_discount=-20.0)
        )

        self.assertTrue(documents, "Changing the markup moved no shelf price")
        line = self._line_for(documents, self.product_retail)
        self.assertAlmostEqual(line.old_price_with_vat, 119.0, places=2)
        self.assertAlmostEqual(line.new_price_with_vat, 142.8, places=2)

    def test_surcharge_and_rounding_are_watched_too(self):
        """Every term of a formula answers with a price."""
        item = self._new_item(
            pricelist_id=self.pricelist_mag1.id,
            applied_on="0_product_variant",
            product_id=self.product_retail.id,
            compute_price="formula",
            base="list_price",
            price_discount=0.0,
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)

        documents = self._documents_raised_by(
            lambda: self._edit(item, price_surcharge=10.0)
        )

        self.assertTrue(documents, "An extra fee moved no shelf price")
        self.assertAlmostEqual(
            self._line_for(documents, self.product_retail).new_price_with_vat,
            129.0,
            places=2,
        )

    def test_percentage_rule_change_raises_a_document(self):
        """A discount rule prices the shelf as much as a fixed rule does."""
        item = self._new_item(
            pricelist_id=self.pricelist_mag1.id,
            applied_on="0_product_variant",
            product_id=self.product_retail.id,
            compute_price="percentage",
            percent_price=10.0,
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)

        documents = self._documents_raised_by(
            lambda: self._edit(item, percent_price=20.0)
        )

        self.assertTrue(documents, "A percentage rule moved no shelf price")
        self.assertAlmostEqual(
            self._line_for(documents, self.product_retail).new_price_with_vat,
            95.2,
            places=2,
        )

    # ------------------------------------------------------------------
    # A price decided on another list
    # ------------------------------------------------------------------
    def _price_mag1_off_a_base_list(self, markup_discount=0.0):
        """Make MAG1 price its shelves as a formula over a buying list.

        The new global rule wins over the one the fixture created: both are
        global with no minimum quantity, so the pricelist orders them by id
        descending and the newer answers first.
        """
        base_list = self.env["product.pricelist"].create(
            {
                "name": "Lista de achizitie",
                "currency_id": self.env.company.currency_id.id,
                "company_id": self.env.company.id,
            }
        )
        base_item = self._new_item(
            pricelist_id=base_list.id,
            applied_on="0_product_variant",
            product_id=self.product_retail.id,
            compute_price="fixed",
            fixed_price=100.0,
        )
        self._new_item(
            pricelist_id=self.pricelist_mag1.id,
            applied_on="3_global",
            compute_price="formula",
            base="pricelist",
            base_pricelist_id=base_list.id,
            price_discount=markup_discount,
        )
        return base_list, base_item

    def test_change_on_the_base_pricelist_raises_a_document(self):
        """The buyer moves a price on the list the shop derives from.

        Every label in the shop moves with it, and the rule that was written
        does not live on the shop's own pricelist - which is exactly why this
        went unnoticed.
        """
        _base_list, base_item = self._price_mag1_off_a_base_list()
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)

        documents = self._documents_raised_by(
            lambda: self._edit(base_item, fixed_price=130.0)
        )

        self.assertTrue(documents, "A change on the base pricelist moved nothing")
        self.assertEqual(documents.warehouse_id, self.warehouse_mag1)
        line = self._line_for(documents, self.product_retail)
        self.assertAlmostEqual(line.old_price_with_vat, 100.0, places=2)
        self.assertAlmostEqual(line.new_price_with_vat, 130.0, places=2)

    def test_the_markup_over_the_base_list_is_applied(self):
        """The document holds the shelf price, not the price of the base list."""
        _base_list, base_item = self._price_mag1_off_a_base_list(markup_discount=-25.0)
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)

        documents = self._documents_raised_by(
            lambda: self._edit(base_item, fixed_price=200.0)
        )

        self.assertTrue(documents)
        self.assertAlmostEqual(
            self._line_for(documents, self.product_retail).new_price_with_vat,
            250.0,
            places=2,
        )

    def test_a_chain_of_pricelists_is_followed_to_the_end(self):
        """A list derived from a list derived from the edited one."""
        root = self.env["product.pricelist"].create(
            {
                "name": "Lista radacina",
                "currency_id": self.env.company.currency_id.id,
                "company_id": self.env.company.id,
            }
        )
        middle = self.env["product.pricelist"].create(
            {
                "name": "Lista intermediara",
                "currency_id": self.env.company.currency_id.id,
                "company_id": self.env.company.id,
            }
        )
        root_item = self._new_item(
            pricelist_id=root.id,
            applied_on="0_product_variant",
            product_id=self.product_retail.id,
            compute_price="fixed",
            fixed_price=100.0,
        )
        self._new_item(
            pricelist_id=middle.id,
            applied_on="3_global",
            compute_price="formula",
            base="pricelist",
            base_pricelist_id=root.id,
            price_discount=0.0,
        )
        self._new_item(
            pricelist_id=self.pricelist_mag1.id,
            applied_on="3_global",
            compute_price="formula",
            base="pricelist",
            base_pricelist_id=middle.id,
            price_discount=0.0,
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)

        documents = self._documents_raised_by(
            lambda: self._edit(root_item, fixed_price=160.0)
        )

        self.assertTrue(documents, "The chain to the shop's list was not followed")
        self.assertAlmostEqual(
            self._line_for(documents, self.product_retail).new_price_with_vat,
            160.0,
            places=2,
        )

    def test_an_unrelated_pricelist_raises_nothing(self):
        """Only the lists a shop actually prices from are followed."""
        unrelated = self.env["product.pricelist"].create(
            {
                "name": "Lista fara legatura",
                "currency_id": self.env.company.currency_id.id,
                "company_id": self.env.company.id,
            }
        )
        item = self._new_item(
            pricelist_id=unrelated.id,
            applied_on="0_product_variant",
            product_id=self.product_retail.id,
            compute_price="fixed",
            fixed_price=100.0,
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)

        documents = self._documents_raised_by(
            lambda: self._edit(item, fixed_price=500.0)
        )

        self.assertFalse(
            documents,
            "A pricelist no shop prices from raised a price change document",
        )

    # ------------------------------------------------------------------
    # The sale price is the shelf price, for most shops
    # ------------------------------------------------------------------
    def test_changing_the_sale_price_raises_a_document(self):
        """``base='list_price'`` is the default, and the fixture's own setup.

        For that shop the repricing action is editing the product, and nothing
        is written on the pricelist at all.
        """
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)

        documents = self._documents_raised_by(
            lambda: self.product_retail.product_tmpl_id.write({"list_price": 238.0})
        )

        self.assertTrue(documents, "Changing the sale price moved no shelf price")
        line = self._line_for(documents, self.product_retail)
        self.assertAlmostEqual(line.old_price_with_vat, 119.0, places=2)
        self.assertAlmostEqual(line.new_price_with_vat, 238.0, places=2)

    def test_sale_price_change_without_retail_stock_raises_nothing(self):
        """A document has nothing to say about goods that are not on a shelf."""
        documents = self._documents_raised_by(
            lambda: self.product_retail.product_tmpl_id.write({"list_price": 238.0})
        )
        self.assertFalse(documents)

    def test_sale_price_change_is_ignored_where_the_shelf_does_not_follow_it(self):
        """A shop priced off a fixed rule does not move when the product does."""
        self._new_item(
            pricelist_id=self.pricelist_mag1.id,
            applied_on="0_product_variant",
            product_id=self.product_retail.id,
            compute_price="fixed",
            fixed_price=150.0,
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)

        documents = self._documents_raised_by(
            lambda: self.product_retail.product_tmpl_id.write({"list_price": 999.0})
        )

        self.assertFalse(
            documents,
            "The sale price moved a shelf that is priced by a fixed rule",
        )

    # ------------------------------------------------------------------
    # Creating a rule
    # ------------------------------------------------------------------
    def test_creating_a_rule_that_changes_nothing_raises_nothing(self):
        """A new rule has no price from before, so it is judged against 371.

        Compared against nothing instead - as though every price had moved up
        from zero - a rule covering a category handed the shop a draft listing
        its whole assortment, every line of it agreeing with itself.
        """
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)

        documents = self._documents_raised_by(
            lambda: self.Item.create(
                {
                    "pricelist_id": self.pricelist_mag1.id,
                    "applied_on": "2_product_category",
                    "categ_id": self.product_retail.categ_id.id,
                    "compute_price": "fixed",
                    # Exactly what the shelf already carries.
                    "fixed_price": 119.0,
                }
            )
        )

        self.assertFalse(
            documents,
            "A rule that priced the shelf where it already stood raised a document",
        )

    def test_creating_a_rule_that_moves_the_price_raises_a_document(self):
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)

        documents = self._documents_raised_by(
            lambda: self.Item.create(
                {
                    "pricelist_id": self.pricelist_mag1.id,
                    "applied_on": "2_product_category",
                    "categ_id": self.product_retail.categ_id.id,
                    "compute_price": "fixed",
                    "fixed_price": 190.0,
                }
            )
        )

        self.assertTrue(documents, "A new category rule moved no shelf price")
        line = self._line_for(documents, self.product_retail)
        self.assertAlmostEqual(line.old_price_with_vat, 119.0, places=2)
        self.assertAlmostEqual(line.new_price_with_vat, 190.0, places=2)

    # ------------------------------------------------------------------
    # One open draft per shop
    # ------------------------------------------------------------------
    def test_repeated_moves_top_up_one_draft(self):
        """Three price moves in a morning are one document, not three.

        Each extra draft quotes a price that is no longer the one on the
        label, and the nightly reconciliation would add one more every night
        until somebody posted them.
        """
        item = self._new_item(
            pricelist_id=self.pricelist_mag1.id,
            applied_on="0_product_variant",
            product_id=self.product_retail.id,
            compute_price="fixed",
            fixed_price=150.0,
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)

        documents = self._documents_raised_by(
            lambda: [
                self._edit(item, fixed_price=160.0),
                self._edit(item, fixed_price=170.0),
                self._edit(item, fixed_price=185.0),
            ]
        )

        self.assertEqual(
            len(documents), 1, "Each price move raised a document of its own"
        )
        line = self._line_for(documents, self.product_retail)
        self.assertEqual(len(line), 1)
        self.assertAlmostEqual(
            line.new_price_with_vat,
            185.0,
            places=2,
            msg="The open draft still quotes a superseded price",
        )

    def test_a_posted_document_does_not_hold_back_the_next_one(self):
        """Topping up applies to the open draft, not to a closed one."""
        item = self._new_item(
            pricelist_id=self.pricelist_mag1.id,
            applied_on="0_product_variant",
            product_id=self.product_retail.id,
            compute_price="fixed",
            fixed_price=150.0,
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        first = self._documents_raised_by(lambda: self._edit(item, fixed_price=160.0))
        first.action_post()
        self.assertEqual(first.state, "done")

        second = self._documents_raised_by(lambda: self._edit(item, fixed_price=175.0))

        self.assertTrue(second, "A posted document swallowed the next price move")
        self.assertNotEqual(first, second)

    # ------------------------------------------------------------------
    # Posting must not dismantle the way the shop prices
    # ------------------------------------------------------------------
    def _variant_overrides(self, pricelist, product):
        return self.Item.search(
            [
                ("pricelist_id", "=", pricelist.id),
                ("applied_on", "=", "0_product_variant"),
                ("product_id", "=", product.id),
                ("compute_price", "=", "fixed"),
            ]
        )

    def test_posting_a_formula_driven_document_writes_no_fixed_rule(self):
        """The regression this family of modules was quietly suffering.

        A document raised by a category rule was posted, and on its way out it
        pinned every article to a fixed price - so the rule that produced the
        price stopped reaching them, and after a few rounds the shop had one
        fixed rule per article and no formula left.
        """
        item = self._new_item(
            pricelist_id=self.pricelist_mag1.id,
            applied_on="2_product_category",
            categ_id=self.product_retail.categ_id.id,
            compute_price="fixed",
            fixed_price=150.0,
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        document = self._documents_raised_by(
            lambda: self._edit(item, fixed_price=180.0)
        )
        self.assertTrue(document)

        document.action_post()

        self.assertEqual(document.state, "done")
        self.assertFalse(
            self._variant_overrides(self.pricelist_mag1, self.product_retail),
            "Posting pinned a fixed price over the category rule that set it",
        )
        # The shop still prices the way it was set up to.
        self.assertAlmostEqual(
            self.product_retail._l10n_ro_get_retail_price(
                warehouse=self.warehouse_mag1, company=self.env.company
            ),
            180.0,
            places=2,
        )

    def test_posting_a_hand_typed_price_does_write_a_fixed_rule(self):
        """An override is written when the user actually overrode something."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        document = self.Document.create({"warehouse_id": self.warehouse_mag1.id})
        document.action_load_products()
        line = self._line_for(document, self.product_retail)
        line.new_price_with_vat = 250.0

        document.action_post()

        override = self._variant_overrides(self.pricelist_mag1, self.product_retail)
        self.assertTrue(
            override, "A price the pricelist does not produce was not written"
        )
        self.assertAlmostEqual(override.fixed_price, 250.0, places=2)

    # ------------------------------------------------------------------
    # Prices that move with nobody writing anything
    # ------------------------------------------------------------------
    def test_cron_raises_a_document_for_a_price_that_moved_by_itself(self):
        """The label and account 371 no longer agree, and no hook could know.

        A dated promotion opening, a formula over the cost re-priced by a
        reception, a change of VAT rate - all of them move the price with
        nothing written on the pricelist. Simulated here by moving the price
        behind the hook's back, which is what those cases amount to.
        """
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        self._new_item(
            pricelist_id=self.pricelist_mag1.id,
            applied_on="0_product_variant",
            product_id=self.product_retail.id,
            compute_price="fixed",
            fixed_price=175.0,
        )

        documents = self._documents_raised_by(
            lambda: self.Document._cron_reconcile_shelf_prices()
        )

        self.assertTrue(documents, "The reconciliation found no drift")
        self.assertEqual(documents.warehouse_id, self.warehouse_mag1)
        line = self._line_for(documents, self.product_retail)
        self.assertAlmostEqual(line.old_price_with_vat, 119.0, places=2)
        self.assertAlmostEqual(line.new_price_with_vat, 175.0, places=2)

    def test_cron_is_quiet_when_the_label_and_the_account_agree(self):
        """The invariant holds, so there is nothing to raise."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)

        documents = self._documents_raised_by(
            lambda: self.Document._cron_reconcile_shelf_prices()
        )

        self.assertFalse(
            documents, "The reconciliation raised a document over no drift at all"
        )

    def test_cron_runs_twice_without_stacking_documents(self):
        """A divergence nobody has posted yet is not raised again every night."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        self._new_item(
            pricelist_id=self.pricelist_mag1.id,
            applied_on="0_product_variant",
            product_id=self.product_retail.id,
            compute_price="fixed",
            fixed_price=175.0,
        )

        documents = self._documents_raised_by(
            lambda: [
                self.Document._cron_reconcile_shelf_prices(),
                self.Document._cron_reconcile_shelf_prices(),
            ]
        )

        self.assertEqual(
            len(documents),
            1,
            "The reconciliation raised the same divergence twice",
        )

    def test_cron_leaves_stock_the_ledger_does_not_account_for_alone(self):
        """That is the opening balance, and it has a wizard of its own.

        A document raised over it would refuse to post anyway: the rate it
        applies is derived from the ledger it would be contradicting.
        """
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        self.env["l10n.ro.retail.markup.line"].sudo().search(
            [
                ("warehouse_id", "=", self.warehouse_mag1.id),
                ("product_id", "=", self.product_retail.id),
            ]
        ).unlink()
        self._new_item(
            pricelist_id=self.pricelist_mag1.id,
            applied_on="0_product_variant",
            product_id=self.product_retail.id,
            compute_price="fixed",
            fixed_price=175.0,
        )

        documents = self._documents_raised_by(
            lambda: self.Document._cron_reconcile_shelf_prices()
        )

        self.assertFalse(
            documents,
            "The reconciliation raised an unpostable document over unsettled "
            "opening stock",
        )

    def test_cron_ignores_a_product_with_no_shelf_price(self):
        """An unpriced article is not a price that dropped to zero."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        # Strip MAG1 of every rule, so the pricelist answers with nothing.
        self.Item.with_context(skip_retail_price_change=True).search(
            [("pricelist_id", "=", self.pricelist_mag1.id)]
        ).unlink()

        documents = self._documents_raised_by(
            lambda: self.Document._cron_reconcile_shelf_prices()
        )

        self.assertFalse(
            documents,
            "An article with no rule was revalued down to nothing",
        )
