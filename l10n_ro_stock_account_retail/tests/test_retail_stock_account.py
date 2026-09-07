# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestRetailCommon


@tagged("post_install", "-at_install")
class TestRetailStockAccount(TestRetailCommon):
    def test_location_inherits_retail_flag(self):
        self.assertTrue(self.retail_stock_loc.l10n_ro_retail)
        self.retail_warehouse.l10n_ro_retail = False
        self.retail_stock_loc.invalidate_recordset()
        self.assertFalse(self.retail_stock_loc.l10n_ro_retail)

    def test_retail_price_split(self):
        prices = self.product_retail._l10n_ro_get_retail_prices(
            warehouse=self.retail_warehouse, company=self.env.company
        )
        self.assertAlmostEqual(prices["price_without_vat"], 100.0, places=2)
        self.assertAlmostEqual(prices["price_with_vat"], 119.0, places=2)
        self.assertAlmostEqual(prices["vat"], 19.0, places=2)

    def test_account_resolution_company_fallback(self):
        account = self.retail_stock_loc._l10n_ro_get_markup_account(
            product=self.product_retail
        )
        self.assertEqual(account, self.account_378)
        account = self.retail_stock_loc._l10n_ro_get_deferred_vat_account(
            product=self.product_retail
        )
        self.assertEqual(account, self.account_4428)

    def test_account_resolution_location_override(self):
        other_account = self.env["account.account"].create(
            {
                "code": "378locret",
                "name": "Markup location override",
                "account_type": "asset_current",
                "company_ids": [(4, self.env.company.id)],
            }
        )
        self.retail_stock_loc.l10n_ro_account_markup_id = other_account
        account = self.retail_stock_loc._l10n_ro_get_markup_account(
            product=self.product_retail
        )
        self.assertEqual(account, other_account)

    def test_account_resolution_product_then_category(self):
        cat_account = self.env["account.account"].create(
            {
                "code": "378catret",
                "name": "Markup cat",
                "account_type": "asset_current",
                "company_ids": [(4, self.env.company.id)],
            }
        )
        prod_account = self.env["account.account"].create(
            {
                "code": "378prodret",
                "name": "Markup prod",
                "account_type": "asset_current",
                "company_ids": [(4, self.env.company.id)],
            }
        )
        self.product_retail.categ_id.l10n_ro_account_markup_id = cat_account
        self.assertEqual(
            self.retail_stock_loc._l10n_ro_get_markup_account(
                product=self.product_retail
            ),
            cat_account,
        )
        self.product_retail.l10n_ro_account_markup_id = prod_account
        self.assertEqual(
            self.retail_stock_loc._l10n_ro_get_markup_account(
                product=self.product_retail
            ),
            prod_account,
        )

    # -------------------------------------------------------------------
    # Transfer helpers
    # -------------------------------------------------------------------
    # -------------------------------------------------------------------
    # Internal transfers between a non-retail depot and retail stores
    # -------------------------------------------------------------------
    def test_transfer_depot_to_store_journal_entries(self):
        """Depozit (non-retail) -> MAG1 (retail): the main valuation entry
        moves cost from the depot's default 371 to MAG1's own 371 through
        the 482 settlement account, and a separate retail entry books the
        378/4428 markup for the incoming goods (only one leg: 'in')."""
        self._set_initial_stock(self.location, self.product_retail, 10)
        move = self._do_transfer(self.location, self.loc_mag1, self.product_retail, 4)

        cost = 4 * self.product_retail.standard_price  # 200.0
        main_move = move.account_move_id
        self.assertTrue(main_move, "No main valuation move created")
        self.assertEqual(
            self._lines_as_tuples(main_move),
            sorted(
                [
                    (self.account_482.id, cost, 0.0),
                    (self.account_371.id, 0.0, cost),
                    (self.account_371_mag1.id, cost, 0.0),
                    (self.account_482.id, 0.0, cost),
                ]
            ),
        )

        extra_move = self.env["account.move"].search(
            [("l10n_ro_extra_stock_move_id", "=", move.id)]
        )
        self.assertTrue(extra_move, "No retail markup move created")
        markup = 4 * (100.0 - self.product_retail.standard_price)  # 200.0
        vat = 4 * 19.0  # 76.0
        self.assertEqual(
            self._lines_as_tuples(extra_move),
            sorted(
                [
                    (self.account_371_mag1.id, markup, 0.0),
                    (self.account_378_mag1.id, 0.0, markup),
                    (self.account_371_mag1.id, vat, 0.0),
                    (self.account_4428_mag1.id, 0.0, vat),
                ]
            ),
        )

    def test_transfer_store_to_depot_journal_entries(self):
        """MAG1 (retail) -> Depozit (non-retail): reverse direction, only
        one retail leg ('out'), releasing MAG1's markup/VAT."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        move = self._do_transfer(self.loc_mag1, self.location, self.product_retail, 4)

        cost = 4 * self.product_retail.standard_price
        main_move = move.account_move_id
        self.assertEqual(
            self._lines_as_tuples(main_move),
            sorted(
                [
                    (self.account_482.id, cost, 0.0),
                    (self.account_371_mag1.id, 0.0, cost),
                    (self.account_371.id, cost, 0.0),
                    (self.account_482.id, 0.0, cost),
                ]
            ),
        )

        extra_move = self.env["account.move"].search(
            [("l10n_ro_extra_stock_move_id", "=", move.id)]
        )
        self.assertTrue(extra_move, "No retail markup move created")
        markup = 4 * (100.0 - self.product_retail.standard_price)
        vat = 4 * 19.0
        self.assertEqual(
            self._lines_as_tuples(extra_move),
            sorted(
                [
                    (self.account_378_mag1.id, markup, 0.0),
                    (self.account_371_mag1.id, 0.0, markup),
                    (self.account_4428_mag1.id, vat, 0.0),
                    (self.account_371_mag1.id, 0.0, vat),
                ]
            ),
        )

    # -------------------------------------------------------------------
    # Internal transfer between two retail stores
    # -------------------------------------------------------------------
    def test_transfer_between_two_stores_journal_entries(self):
        """MAG1 -> MAG2 (both retail, different warehouses): the main
        valuation entry moves cost from MAG1's 371 to MAG2's 371 through
        482, and the retail entry has BOTH legs: 'out' at MAG1 (releasing
        its markup/VAT) and 'in' at MAG2 (booking its own markup/VAT) -
        each leg must hit its OWN store's accounts, never the other
        store's."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        move = self._do_transfer(self.loc_mag1, self.loc_mag2, self.product_retail, 4)

        cost = 4 * self.product_retail.standard_price
        main_move = move.account_move_id
        self.assertEqual(
            self._lines_as_tuples(main_move),
            sorted(
                [
                    (self.account_482.id, cost, 0.0),
                    (self.account_371_mag1.id, 0.0, cost),
                    (self.account_371_mag2.id, cost, 0.0),
                    (self.account_482.id, 0.0, cost),
                ]
            ),
        )

        extra_move = self.env["account.move"].search(
            [("l10n_ro_extra_stock_move_id", "=", move.id)]
        )
        self.assertTrue(extra_move, "No retail markup move created")
        markup = 4 * (100.0 - self.product_retail.standard_price)
        vat = 4 * 19.0
        self.assertEqual(
            self._lines_as_tuples(extra_move),
            sorted(
                [
                    # 'out' leg at MAG1: releases its own markup/VAT
                    (self.account_378_mag1.id, markup, 0.0),
                    (self.account_371_mag1.id, 0.0, markup),
                    (self.account_4428_mag1.id, vat, 0.0),
                    (self.account_371_mag1.id, 0.0, vat),
                    # 'in' leg at MAG2: books its own markup/VAT
                    (self.account_371_mag2.id, markup, 0.0),
                    (self.account_378_mag2.id, 0.0, markup),
                    (self.account_371_mag2.id, vat, 0.0),
                    (self.account_4428_mag2.id, 0.0, vat),
                ]
            ),
        )
        # Both stores' own markup/VAT accounts are present (no leg is
        # silently dropped or booked on the wrong store's accounts).
        account_ids = {line.account_id.id for line in extra_move.line_ids}
        mag1_accounts = {self.account_378_mag1.id, self.account_4428_mag1.id}
        mag2_accounts = {self.account_378_mag2.id, self.account_4428_mag2.id}
        self.assertTrue(mag1_accounts <= account_ids)
        self.assertTrue(mag2_accounts <= account_ids)

    # -------------------------------------------------------------------
    # "External" movements: purchase receipts and sale deliveries
    # -------------------------------------------------------------------
    def test_purchase_receipt_into_store_creates_retail_markup(self):
        """Receiving goods straight from a supplier into MAG1 (no internal
        transfer involved). A plain reception (no 'aviz'/notice) doesn't
        book any cost valuation by itself in this localization - that only
        happens once the vendor bill is posted, matching the Romanian
        practice of deferring the accounting entry until the invoice
        arrives. The retail markup/VAT, however, is booked right at
        picking validation (a single 'in' leg, there is no source retail
        location), directly on MAG1's own accounts."""
        po, move = self._do_purchase_receipt(
            self.warehouse_mag1, self.product_retail, 4, 50.0
        )
        cost = 4 * 50.0

        extra_move = self.env["account.move"].search(
            [("l10n_ro_extra_stock_move_id", "=", move.id)]
        )
        self.assertTrue(extra_move, "No retail markup move created")
        markup = 4 * (100.0 - 50.0)
        vat = 4 * 19.0
        self.assertEqual(
            self._lines_as_tuples(extra_move),
            sorted(
                [
                    (self.account_371_mag1.id, markup, 0.0),
                    (self.account_378_mag1.id, 0.0, markup),
                    (self.account_371_mag1.id, vat, 0.0),
                    (self.account_4428_mag1.id, 0.0, vat),
                ]
            ),
        )

        # The cost itself lands on MAG1's own 371 once the vendor bill
        # (which carries the actual purchase price) is posted.
        action = po.action_create_invoice()
        invoice = self.env["account.move"].browse(action["res_id"])
        invoice.invoice_date = invoice.date
        invoice.action_post()
        self.assertIn(
            (self.account_371_mag1.id, cost, 0.0),
            self._lines_as_tuples(invoice),
        )

    def test_sale_delivery_from_store_releases_retail_markup(self):
        """Delivering to a customer from MAG1: the delivery credits MAG1's
        371 and debits MAG1's own 607 expense account, and the retail
        entry releases the markup/VAT (a single 'out' leg, there is no
        destination retail location)."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        move = self._do_sale_delivery(
            self.warehouse_mag1, self.product_retail, 4, 100.0
        )
        cost = 4 * self.product_retail.standard_price
        main_move = move.account_move_id
        self.assertTrue(main_move, "No main valuation move created")
        self.assertEqual(
            self._lines_as_tuples(main_move),
            sorted(
                [
                    (self.account_607_mag1.id, cost, 0.0),
                    (self.account_371_mag1.id, 0.0, cost),
                ]
            ),
        )

        extra_move = self.env["account.move"].search(
            [("l10n_ro_extra_stock_move_id", "=", move.id)]
        )
        self.assertTrue(extra_move, "No retail markup move created")
        markup = 4 * (100.0 - self.product_retail.standard_price)
        vat = 4 * 19.0
        self.assertEqual(
            self._lines_as_tuples(extra_move),
            sorted(
                [
                    (self.account_378_mag1.id, markup, 0.0),
                    (self.account_371_mag1.id, 0.0, markup),
                    (self.account_4428_mag1.id, vat, 0.0),
                    (self.account_371_mag1.id, 0.0, vat),
                ]
            ),
        )

    # -------------------------------------------------------------------
    # Returns
    # -------------------------------------------------------------------
    def test_transfer_return_between_stores_journal_entries(self):
        """MAG1 -> MAG2, then return the goods MAG2 -> MAG1. A return of an
        internal transfer is classified as a plain 'internal_transfer'
        again (there's no dedicated return type for internal-to-internal
        moves), so it must book a fresh, correctly-split entry: this time
        crediting MAG2's own 371 and debiting MAG1's own 371, with the
        retail entry mirroring the original ('out' at MAG2, 'in' at MAG1)."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        move = self._do_transfer(self.loc_mag1, self.loc_mag2, self.product_retail, 4)
        return_move = self._do_return(move.picking_id, 4)

        cost = 4 * self.product_retail.standard_price
        self.assertEqual(return_move.l10n_ro_move_type, "internal_transfer")
        main_move = return_move.account_move_id
        self.assertTrue(main_move, "No main valuation move created for the return")
        self.assertEqual(
            self._lines_as_tuples(main_move),
            sorted(
                [
                    (self.account_482.id, cost, 0.0),
                    (self.account_371_mag2.id, 0.0, cost),
                    (self.account_371_mag1.id, cost, 0.0),
                    (self.account_482.id, 0.0, cost),
                ]
            ),
        )

        extra_move = self.env["account.move"].search(
            [("l10n_ro_extra_stock_move_id", "=", return_move.id)]
        )
        self.assertTrue(extra_move, "No retail markup move created for the return")
        markup = 4 * (100.0 - self.product_retail.standard_price)
        vat = 4 * 19.0
        self.assertEqual(
            self._lines_as_tuples(extra_move),
            sorted(
                [
                    # 'out' leg at MAG2: releases its own markup/VAT
                    (self.account_378_mag2.id, markup, 0.0),
                    (self.account_371_mag2.id, 0.0, markup),
                    (self.account_4428_mag2.id, vat, 0.0),
                    (self.account_371_mag2.id, 0.0, vat),
                    # 'in' leg at MAG1: books its own markup/VAT back
                    (self.account_371_mag1.id, markup, 0.0),
                    (self.account_378_mag1.id, 0.0, markup),
                    (self.account_371_mag1.id, vat, 0.0),
                    (self.account_4428_mag1.id, 0.0, vat),
                ]
            ),
        )

    def test_sale_return_into_store_journal_entries(self):
        """Customer returns goods sold from MAG1: goods flow back in from
        outside the company into a retail location, so the retail entry
        has a single 'in' leg, re-booking MAG1's own markup/VAT (same
        accounts, same sides as a normal incoming leg - a return doesn't
        change which accounts/sides are used, only that it happens on a
        'delivery_return' move instead of a fresh 'internal_transfer')."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        move = self._do_sale_delivery(
            self.warehouse_mag1, self.product_retail, 4, 100.0
        )
        return_move = self._do_return(move.picking_id, 4)

        self.assertEqual(return_move.l10n_ro_move_type, "delivery_return")
        extra_move = self.env["account.move"].search(
            [("l10n_ro_extra_stock_move_id", "=", return_move.id)]
        )
        self.assertTrue(extra_move, "No retail markup move created for the return")
        markup = 4 * (100.0 - self.product_retail.standard_price)
        vat = 4 * 19.0
        self.assertEqual(
            self._lines_as_tuples(extra_move),
            sorted(
                [
                    (self.account_371_mag1.id, markup, 0.0),
                    (self.account_378_mag1.id, 0.0, markup),
                    (self.account_371_mag1.id, vat, 0.0),
                    (self.account_4428_mag1.id, 0.0, vat),
                ]
            ),
        )

    def test_purchase_return_from_store_journal_entries(self):
        """MAG1 returns goods to the supplier: goods flow out of the store
        to outside the company, so the retail entry has a single 'out'
        leg, releasing MAG1's own markup/VAT - same accounts/sides as any
        other outgoing leg, just on a 'reception_return' move (which,
        like a plain reception, books no main valuation entry until a
        credit note is posted)."""
        po, move = self._do_purchase_receipt(
            self.warehouse_mag1, self.product_retail, 4, 50.0
        )
        return_move = self._do_return(move.picking_id, 4)

        self.assertEqual(return_move.l10n_ro_move_type, "reception_return")
        extra_move = self.env["account.move"].search(
            [("l10n_ro_extra_stock_move_id", "=", return_move.id)]
        )
        self.assertTrue(extra_move, "No retail markup move created for the return")
        markup = 4 * (100.0 - 50.0)
        vat = 4 * 19.0
        self.assertEqual(
            self._lines_as_tuples(extra_move),
            sorted(
                [
                    (self.account_378_mag1.id, markup, 0.0),
                    (self.account_371_mag1.id, 0.0, markup),
                    (self.account_4428_mag1.id, vat, 0.0),
                    (self.account_371_mag1.id, 0.0, vat),
                ]
            ),
        )

    # -------------------------------------------------------------------
    # Edge cases
    # -------------------------------------------------------------------
    def test_transfer_within_same_retail_warehouse_no_retail_entry(self):
        """Moving stock between two internal locations of the SAME retail
        warehouse must NOT create a retail markup entry - both legs would
        hit the same store's accounts, so `_l10n_ro_retail_legs()` short-
        circuits to an empty list (checked explicitly: `src_wh == dest_wh`
        -> return [])."""
        sub_loc = self.env["stock.location"].create(
            {
                "name": "MAG1 Sub",
                "usage": "internal",
                "location_id": self.loc_mag1.id,
            }
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        move = self._do_transfer(self.loc_mag1, sub_loc, self.product_retail, 4)
        extra_move = self.env["account.move"].search(
            [("l10n_ro_extra_stock_move_id", "=", move.id)]
        )
        self.assertFalse(
            extra_move, "A retail entry should not be created within the same store"
        )

    def test_partial_return_journal_entries(self):
        """Transfer 10 units MAG1 -> MAG2, then return only 4 of them. The
        return's retail entry must reflect the PARTIAL quantity, not the
        original transfer's full amount."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        move = self._do_transfer(self.loc_mag1, self.loc_mag2, self.product_retail, 10)
        return_move = self._do_return(move.picking_id, 4)

        extra_move = self.env["account.move"].search(
            [("l10n_ro_extra_stock_move_id", "=", return_move.id)]
        )
        self.assertTrue(extra_move, "No retail markup move created for the return")
        markup = 4 * (100.0 - self.product_retail.standard_price)
        vat = 4 * 19.0
        self.assertEqual(
            self._lines_as_tuples(extra_move),
            sorted(
                [
                    (self.account_378_mag2.id, markup, 0.0),
                    (self.account_371_mag2.id, 0.0, markup),
                    (self.account_4428_mag2.id, vat, 0.0),
                    (self.account_371_mag2.id, 0.0, vat),
                    (self.account_371_mag1.id, markup, 0.0),
                    (self.account_378_mag1.id, 0.0, markup),
                    (self.account_371_mag1.id, vat, 0.0),
                    (self.account_4428_mag1.id, 0.0, vat),
                ]
            ),
        )

    def test_missing_markup_account_raises(self):
        """If no markup/VAT account can be resolved anywhere (location,
        product, category, or company), booking must fail loudly instead
        of silently landing on the wrong account."""
        self.env.company.l10n_ro_account_markup_id = False
        self.env.company.l10n_ro_account_deferred_vat_id = False
        self._set_initial_stock(self.location, self.product_retail, 10)
        with self.assertRaises(UserError):
            self._do_transfer(
                self.location, self.retail_stock_loc, self.product_retail, 4
            )

    def test_zero_markup_creates_no_retail_entry(self):
        """A product sold at exactly its cost, with no tax, has zero
        markup and zero VAT - no retail entry should be booked at all."""
        product_no_markup = self.env["product.product"].create(
            {
                "name": "Produs fara adaos",
                "is_storable": True,
                "categ_id": self.category_marfa_avg.id,
                "list_price": 50.0,
                "standard_price": 50.0,
                "taxes_id": [(6, 0, [])],
            }
        )
        self._set_initial_stock(self.location, product_no_markup, 10)
        move = self._do_transfer(self.location, self.loc_mag1, product_no_markup, 4)
        extra_move = self.env["account.move"].search(
            [("l10n_ro_extra_stock_move_id", "=", move.id)]
        )
        self.assertFalse(
            extra_move, "No retail entry should be booked when markup/VAT are zero"
        )

    # -------------------------------------------------------------------
    # Price source: pricelist vs. actual sale price/discount
    # -------------------------------------------------------------------
    def test_sale_discount_does_not_affect_retail_markup(self):
        """Whether the sale line carries the full pricelist price, a
        lower manual price, or an explicit discount %, the retail
        markup/VAT released always reflects the STORE's pricelist price -
        never the actual negotiated sale price. The discount is real (it
        halves the sale's own revenue) - it just never reaches 371/378/
        4428, which track shelf price, not transaction price."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        move = self._do_sale_delivery(
            self.warehouse_mag1, self.product_retail, 4, 100.0, discount=50.0
        )
        sale_line = move.sale_line_id
        self.assertAlmostEqual(sale_line.price_unit, 100.0, places=2)
        self.assertAlmostEqual(sale_line.price_subtotal, 200.0, places=2)  # 4*100*0.5

        extra_move = self.env["account.move"].search(
            [("l10n_ro_extra_stock_move_id", "=", move.id)]
        )
        self.assertTrue(extra_move, "No retail markup move created")
        markup = 4 * (100.0 - self.product_retail.standard_price)
        vat = 4 * 19.0
        self.assertEqual(
            self._lines_as_tuples(extra_move),
            sorted(
                [
                    (self.account_378_mag1.id, markup, 0.0),
                    (self.account_371_mag1.id, 0.0, markup),
                    (self.account_4428_mag1.id, vat, 0.0),
                    (self.account_371_mag1.id, 0.0, vat),
                ]
            ),
        )

    def test_markup_uses_warehouse_pricelist_item_price(self):
        """If MAG1's own retail pricelist has an explicit price for the
        product, the markup/VAT released must be computed from THAT
        price - not from the product's plain list_price fallback, and
        not from whatever price the sale line itself used."""
        self.env["product.pricelist.item"].with_context(
            skip_retail_price_change=True
        ).create(
            {
                "pricelist_id": self.pricelist_mag1.id,
                "applied_on": "0_product_variant",
                "product_id": self.product_retail.id,
                "compute_price": "fixed",
                "fixed_price": 95.2,
            }
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        move = self._do_sale_delivery(
            self.warehouse_mag1, self.product_retail, 4, 100.0
        )

        extra_move = self.env["account.move"].search(
            [("l10n_ro_extra_stock_move_id", "=", move.id)]
        )
        self.assertTrue(extra_move, "No retail markup move created")
        markup = round(4 * (80.0 - self.product_retail.standard_price), 2)  # 120.0
        vat = round(4 * 80.0 * 0.19, 2)  # 60.8
        self.assertEqual(
            self._lines_as_tuples(extra_move),
            sorted(
                [
                    (self.account_378_mag1.id, markup, 0.0),
                    (self.account_371_mag1.id, 0.0, markup),
                    (self.account_4428_mag1.id, vat, 0.0),
                    (self.account_371_mag1.id, 0.0, vat),
                ]
            ),
        )

    # -------------------------------------------------------------------
    # The release must match what was loaded
    # -------------------------------------------------------------------
    def _carried(self, warehouse, product):
        return self.env["l10n.ro.retail.markup.line"]._l10n_ro_carried(
            warehouse, product, self.env.company
        )

    def test_release_uses_loaded_markup_not_current_price(self):
        """Selling after the shelf price moved must release what was loaded.

        Goods enter at a PVA of 119 (cost 50, markup 50, VAT 19 a unit). The
        shelf price is then raised to 178.50 without a Proces Verbal, so
        nothing revalued the stock: 378 and 4428 still hold the old markup.
        Releasing at the new price would take out 100 and 28.50 a unit and
        leave the difference stranded on both accounts for good.
        """
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        markup_in, vat_in = self._carried(self.warehouse_mag1, self.product_retail)
        self.assertAlmostEqual(markup_in, 500.0, places=2)  # 10 * 50
        self.assertAlmostEqual(vat_in, 190.0, places=2)  # 10 * 19

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

        move = self._do_sale_delivery(
            self.warehouse_mag1, self.product_retail, 4, 178.5
        )
        extra_move = self.env["account.move"].search(
            [("l10n_ro_extra_stock_move_id", "=", move.id)]
        )
        self.assertTrue(extra_move, "No retail markup move created")
        self.assertEqual(
            self._lines_as_tuples(extra_move),
            sorted(
                [
                    (self.account_378_mag1.id, 200.0, 0.0),  # 4/10 of 500
                    (self.account_371_mag1.id, 0.0, 200.0),
                    (self.account_4428_mag1.id, 76.0, 0.0),  # 4/10 of 190
                    (self.account_371_mag1.id, 0.0, 76.0),
                ]
            ),
        )

    def test_last_unit_out_closes_markup_accounts(self):
        """Once the shop is empty of a product, 378 and 4428 must hold
        nothing for it - no rounding residue left behind."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 3)
        self._do_sale_delivery(self.warehouse_mag1, self.product_retail, 1, 119.0)
        self._do_sale_delivery(self.warehouse_mag1, self.product_retail, 2, 119.0)
        markup, vat = self._carried(self.warehouse_mag1, self.product_retail)
        self.assertAlmostEqual(markup, 0.0, places=2)
        self.assertAlmostEqual(vat, 0.0, places=2)

    # -------------------------------------------------------------------
    # Selling below cost
    # -------------------------------------------------------------------
    def test_shelf_price_below_cost_is_refused(self):
        """A shelf price under the cost books a negative markup on 378 and
        almost always means the price or the cost is wrong."""
        self.env["product.pricelist.item"].with_context(
            skip_retail_price_change=True
        ).create(
            {
                "pricelist_id": self.pricelist_mag1.id,
                "applied_on": "0_product_variant",
                "product_id": self.product_retail.id,
                "compute_price": "fixed",
                "fixed_price": 35.7,  # 30 net, against a cost of 50
            }
        )
        with self.assertRaises(UserError):
            self._set_initial_stock(self.loc_mag1, self.product_retail, 5)

    def test_shelf_price_below_cost_allowed_when_warehouse_permits(self):
        """A shop that legitimately sells below cost ticks the flag and the
        negative markup is booked as intended."""
        self.warehouse_mag1.l10n_ro_retail_allow_negative_markup = True
        self.env["product.pricelist.item"].with_context(
            skip_retail_price_change=True
        ).create(
            {
                "pricelist_id": self.pricelist_mag1.id,
                "applied_on": "0_product_variant",
                "product_id": self.product_retail.id,
                "compute_price": "fixed",
                "fixed_price": 35.7,
            }
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 5)
        markup, _vat = self._carried(self.warehouse_mag1, self.product_retail)
        self.assertAlmostEqual(markup, 5 * (30.0 - 50.0), places=2)

    # -------------------------------------------------------------------
    # Variants, sublocations, products that carry no stock value
    # -------------------------------------------------------------------
    def test_variants_are_priced_independently(self):
        """Two variants of one template priced differently must each get
        their own shelf price, not the price of the first variant."""
        attribute = self.env["product.attribute"].create(
            {
                "name": "Marime",
                "value_ids": [
                    (0, 0, {"name": "S"}),
                    (0, 0, {"name": "M"}),
                ],
            }
        )
        template = self.env["product.template"].create(
            {
                "name": "Tricou",
                "is_storable": True,
                "categ_id": self.category_marfa_avg.id,
                "list_price": 119.0,
                "taxes_id": [(6, 0, self.tax_19.ids)],
                "attribute_line_ids": [
                    (
                        0,
                        0,
                        {
                            "attribute_id": attribute.id,
                            "value_ids": [(6, 0, attribute.value_ids.ids)],
                        },
                    )
                ],
            }
        )
        variant_s, variant_m = template.product_variant_ids
        Item = self.env["product.pricelist.item"].with_context(
            skip_retail_price_change=True
        )
        for variant, price in ((variant_s, 119.0), (variant_m, 238.0)):
            Item.create(
                {
                    "pricelist_id": self.pricelist_mag1.id,
                    "applied_on": "0_product_variant",
                    "product_id": variant.id,
                    "compute_price": "fixed",
                    "fixed_price": price,
                }
            )
        self.assertAlmostEqual(
            variant_s._l10n_ro_get_retail_price(warehouse=self.warehouse_mag1),
            119.0,
            places=2,
        )
        self.assertAlmostEqual(
            variant_m._l10n_ro_get_retail_price(warehouse=self.warehouse_mag1),
            238.0,
            places=2,
        )

    def test_sublocation_inherits_location_accounts(self):
        """A bin created under the shop stock location uses the shop's 378
        and 4428, not the company defaults."""
        shelf = self.env["stock.location"].create(
            {
                "name": "Raft 1",
                "usage": "internal",
                "location_id": self.loc_mag1.id,
            }
        )
        self.assertTrue(shelf.l10n_ro_retail)
        self.assertEqual(
            shelf._l10n_ro_get_markup_account(product=self.product_retail),
            self.account_378_mag1,
        )
        self.assertEqual(
            shelf._l10n_ro_get_deferred_vat_account(product=self.product_retail),
            self.account_4428_mag1,
        )

    def test_consumable_books_no_retail_entry(self):
        """A product that carries no stock value has no markup to book."""
        consumable = self.env["product.product"].create(
            {
                "name": "Punga",
                "is_storable": False,
                "categ_id": self.category_marfa_avg.id,
                "list_price": 119.0,
                "standard_price": 50.0,
                "taxes_id": [(6, 0, self.tax_19.ids)],
            }
        )
        move = self._do_transfer(self.location, self.loc_mag1, consumable, 4)
        self.assertFalse(
            self.env["account.move"].search(
                [("l10n_ro_extra_stock_move_id", "=", move.id)]
            )
        )
        self.assertFalse(move.l10n_ro_retail_markup_line_ids)

    def test_valuation_taken_from_the_company_when_the_category_is_silent(self):
        """A category that sets no valuation follows the company.

        `property_valuation` is company dependent and routinely left empty, so
        the effective answer comes from `company.inventory_valuation`. Read on
        the category alone it looked like nothing was valued in real time, and
        the whole retail treatment was skipped without a word.
        """
        category = self.env["product.category"].create(
            {
                "name": "Marfa fara setare de evaluare",
                "property_cost_method": "fifo",
                "property_stock_valuation_account_id": self.account_371.id,
                "property_account_expense_categ_id": self.account_expense.id,
            }
        )
        category.property_valuation = False
        self.env.company.inventory_valuation = "real_time"
        product = self.env["product.product"].create(
            {
                "name": "Tigari Premium",
                "is_storable": True,
                "categ_id": category.id,
                "list_price": 119.0,
                "standard_price": 50.0,
                "taxes_id": [(6, 0, self.tax_19.ids)],
            }
        )
        self.assertFalse(category.property_valuation)
        self.assertEqual(product.valuation, "real_time")

        self._set_initial_stock(self.location, product, 10)
        move = self._do_transfer(self.location, self.loc_mag1, product, 4)
        self.assertTrue(
            move.l10n_ro_retail_markup_line_ids,
            "No markup was loaded for a product whose valuation comes from the company",
        )
        markup, vat = self._carried(self.warehouse_mag1, product)
        self.assertAlmostEqual(markup, 200.0, places=2)  # 4 * (100 - 50)
        self.assertAlmostEqual(vat, 76.0, places=2)  # 4 * 19

    def test_periodic_valuation_books_no_retail_entry(self):
        """A company on periodic valuation books nothing in real time, so
        there is no markup to load either."""
        self.env.company.inventory_valuation = "periodic"
        category = self.env["product.category"].create(
            {
                "name": "Marfa evaluata periodic",
                "property_cost_method": "fifo",
                "property_stock_valuation_account_id": self.account_371.id,
                "property_account_expense_categ_id": self.account_expense.id,
            }
        )
        category.property_valuation = False
        product = self.env["product.product"].create(
            {
                "name": "Tigari Standard",
                "is_storable": True,
                "categ_id": category.id,
                "list_price": 119.0,
                "standard_price": 50.0,
                "taxes_id": [(6, 0, self.tax_19.ids)],
            }
        )
        self.assertEqual(product.valuation, "periodic")
        self._set_initial_stock(self.location, product, 10)
        move = self._do_transfer(self.location, self.loc_mag1, product, 4)
        self.assertFalse(move.l10n_ro_retail_markup_line_ids)

    def test_release_rate_ignores_stock_the_ledger_never_saw(self):
        """Stock that predates the module must not dilute the rate.

        A shop that already held goods when this module was installed has
        quants the ledger knows nothing about. Measuring the release against
        the quantity on hand then spreads the little markup that *is* recorded
        over everything on the shelf, so each sale releases a fraction of a leu
        and 378 never closes. The rate is taken from the ledger on both sides,
        so what is recorded is released in full and the accounts close.
        """
        # 40 units already on the shelf, invisible to the ledger - exactly what
        # installing the module onto a running shop leaves behind.
        self._set_initial_stock(self.loc_mag1, self.product_retail, 40)
        # Drop the rows that entry produced: what is left is 40 units on hand
        # that the ledger has no record of.
        self.env["l10n.ro.retail.markup.line"].sudo().search(
            [("product_id", "=", self.product_retail.id)]
        ).unlink()

        # Then two units arrive the normal way and are recorded. The helper
        # sets the count, so 42 is an increase of two over the 40 already there.
        self._set_initial_stock(self.loc_mag1, self.product_retail, 42)
        markup_before, vat_before = self._carried(
            self.warehouse_mag1, self.product_retail
        )
        self.assertAlmostEqual(markup_before, 100.0, places=2)  # 2 * 50

        # Selling more than the ledger accounts for releases all of it.
        self._do_sale_delivery(self.warehouse_mag1, self.product_retail, 20, 119.0)
        markup_after, vat_after = self._carried(
            self.warehouse_mag1, self.product_retail
        )
        self.assertAlmostEqual(markup_after, 0.0, places=2)
        self.assertAlmostEqual(vat_after, 0.0, places=2)

    def test_opening_balance_settles_stock_the_ledger_never_saw(self):
        """The opening balance brings 371 up to shelf price for goods that
        were already on the shelf, and records them so later sales release
        the right amount."""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 40)
        self.env["l10n.ro.retail.markup.line"].sudo().search(
            [("product_id", "=", self.product_retail.id)]
        ).unlink()

        wizard = self.env["l10n.ro.retail.opening.balance"].create(
            {"warehouse_ids": [(6, 0, self.warehouse_mag1.ids)]}
        )
        wizard.action_refresh()
        line = wizard.line_ids.filtered(lambda ln: ln.product_id == self.product_retail)
        self.assertTrue(line, "The opening balance did not see the stock")
        self.assertAlmostEqual(line.quantity, 40.0, places=2)
        self.assertAlmostEqual(line.cost, 2000.0, places=2)  # 40 * 50
        self.assertAlmostEqual(line.markup, 2000.0, places=2)  # 40 * (100 - 50)
        self.assertAlmostEqual(line.vat, 760.0, places=2)  # 40 * 19
        self.assertFalse(line.below_cost)

        wizard.action_post()
        markup, vat = self._carried(self.warehouse_mag1, self.product_retail)
        self.assertAlmostEqual(markup, 2000.0, places=2)
        self.assertAlmostEqual(vat, 760.0, places=2)

        # And the shop now releases the right amount on a sale.
        self._do_sale_delivery(self.warehouse_mag1, self.product_retail, 4, 119.0)
        markup_after, vat_after = self._carried(
            self.warehouse_mag1, self.product_retail
        )
        self.assertAlmostEqual(markup_after, 1800.0, places=2)  # 2000 - 4*50
        self.assertAlmostEqual(vat_after, 684.0, places=2)  # 760 - 4*19

    def test_opening_balance_finds_nothing_on_a_complete_ledger(self):
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        wizard = self.env["l10n.ro.retail.opening.balance"].create(
            {"warehouse_ids": [(6, 0, self.warehouse_mag1.ids)]}
        )
        wizard.action_refresh()
        self.assertFalse(
            wizard.line_ids.filtered(lambda ln: ln.product_id == self.product_retail)
        )

    def test_opening_balance_refuses_goods_priced_below_cost(self):
        self.env["product.pricelist.item"].with_context(
            skip_retail_price_change=True
        ).create(
            {
                "pricelist_id": self.pricelist_mag1.id,
                "applied_on": "0_product_variant",
                "product_id": self.product_retail.id,
                "compute_price": "fixed",
                "fixed_price": 35.7,  # 30 net against a cost of 50
            }
        )
        self.warehouse_mag1.l10n_ro_retail_allow_negative_markup = True
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        self.env["l10n.ro.retail.markup.line"].sudo().search(
            [("product_id", "=", self.product_retail.id)]
        ).unlink()
        self.warehouse_mag1.l10n_ro_retail_allow_negative_markup = False

        wizard = self.env["l10n.ro.retail.opening.balance"].create(
            {"warehouse_ids": [(6, 0, self.warehouse_mag1.ids)]}
        )
        wizard.action_refresh()
        self.assertTrue(wizard.has_shortfall)
        with self.assertRaises(UserError):
            wizard.action_post()

    # -------------------------------------------------------------------
    # The markup is spread over the quantity that was actually valued
    # -------------------------------------------------------------------
    def test_over_receipt_books_markup_on_the_quantity_received(self):
        """Receive 12 against an order for 10.

        No backorder is created - there is nothing left to receive - so the
        move keeps a demand of 10 while core values it at 12. Reading the
        demand made the module divide the cost of twelve units by ten, book
        the markup of ten, and record ten units as carrying it, while 371 had
        already taken the cost of twelve. Cost + markup + VAT stopped adding
        up to 371 on the spot, and every later release rate was computed off
        a quantity smaller than what was on the shelf.
        """
        _po, move = self._do_purchase_receipt(
            self.warehouse_mag1, self.product_retail, 10, 50.0, qty_done=12
        )
        ledger = move.l10n_ro_retail_markup_line_ids
        self.assertEqual(len(ledger), 1)
        self.assertAlmostEqual(ledger.quantity, 12.0, places=2)
        self.assertAlmostEqual(ledger.cost, 12 * 50.0, places=2)
        self.assertAlmostEqual(ledger.markup, 12 * 50.0, places=2)
        self.assertAlmostEqual(ledger.vat, 12 * 19.0, places=2)
        # The whole point: what the row says about 371 is what 371 got.
        self.assertAlmostEqual(ledger.retail_value, 12 * 119.0, places=2)

        extra_move = self.env["account.move"].search(
            [("l10n_ro_extra_stock_move_id", "=", move.id)]
        )
        self.assertEqual(
            self._lines_as_tuples(extra_move),
            sorted(
                [
                    (self.account_371_mag1.id, 600.0, 0.0),
                    (self.account_378_mag1.id, 0.0, 600.0),
                    (self.account_371_mag1.id, 228.0, 0.0),
                    (self.account_4428_mag1.id, 0.0, 228.0),
                ]
            ),
        )

    def test_ledger_row_shares_the_entry_date(self):
        """A row and the entry it belongs to have to fall in the same period,
        or a balance as of a date answers for a different set of movements
        than the trial balance it is reconciled against."""
        _po, move = self._do_purchase_receipt(
            self.warehouse_mag1, self.product_retail, 5, 50.0
        )
        extra_move = self.env["account.move"].search(
            [("l10n_ro_extra_stock_move_id", "=", move.id)]
        )
        self.assertEqual(move.l10n_ro_retail_markup_line_ids.date, extra_move.date)

    # -------------------------------------------------------------------
    # A shelf price has to be configured, not guessed
    # -------------------------------------------------------------------
    def test_missing_shelf_price_is_refused(self):
        """Without a rule on the retail pricelist the module used to fall back
        on the sale price - a price without VAT in any standard Romanian
        setup - and book it on 371 as if it were the price on the label."""
        self.env["product.pricelist.item"].search(
            [("pricelist_id", "=", self.retail_pricelist.id)]
        ).unlink()
        with self.assertRaises(UserError):
            self._set_initial_stock(self.retail_stock_loc, self.product_retail, 5)

    def test_warehouse_without_retail_pricelist_is_refused(self):
        self.retail_warehouse.l10n_ro_retail_pricelist_id = False
        with self.assertRaises(UserError):
            self._set_initial_stock(self.retail_stock_loc, self.product_retail, 5)

    # -------------------------------------------------------------------
    # The shop's fiscal position decides both the taxes and the accounts
    # -------------------------------------------------------------------
    def _make_retail_fiscal_position(self, warehouse, name="Retail"):
        fiscal_position = self.env["account.fiscal.position"].create(
            {"name": name, "company_id": self.env.company.id}
        )
        warehouse.l10n_ro_fiscal_position_id = fiscal_position
        return fiscal_position

    def test_split_follows_the_warehouse_fiscal_position(self):
        """The VAT loaded on 4428 is the one the shop will collect.

        The product carries the 19% domestic tax for everybody else; this shop
        maps it to 9%. Splitting the shelf price with the raw ``taxes_id``
        would load a VAT the till is never going to charge, and leave the
        difference stranded on 4428 for good."""
        fiscal_position = self._make_retail_fiscal_position(self.warehouse_mag1)
        tax_9 = self.env["account.tax"].create(
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
        self.assertEqual(fiscal_position.map_tax(self.tax_19), tax_9)

        prices = self.product_retail._l10n_ro_get_retail_prices(
            warehouse=self.warehouse_mag1
        )
        # 119 on the label, 9% of it VAT: 109.17 base and 9.83 deferred VAT.
        self.assertAlmostEqual(prices["price_with_vat"], 119.0, places=2)
        self.assertAlmostEqual(prices["price_without_vat"], 109.17, places=2)
        self.assertAlmostEqual(prices["vat"], 9.83, places=2)

        # And MAG2, which maps nothing, still splits at 19%.
        prices_mag2 = self.product_retail._l10n_ro_get_retail_prices(
            warehouse=self.warehouse_mag2
        )
        self.assertAlmostEqual(prices_mag2["vat"], 19.0, places=2)

    def test_accounts_follow_the_warehouse_fiscal_position(self):
        """A shop keeping its goods on a 371 of its own maps it once on its
        fiscal position, and the markup and deferred VAT accounts follow the
        same map rather than staying behind in another set of books."""
        fiscal_position = self._make_retail_fiscal_position(self.warehouse_mag1)
        account_371_alt = self.account_371_mag1.copy({"code": "371mag1b"})
        account_378_alt = self.account_378_mag1.copy({"code": "378mag1b"})
        account_4428_alt = self.account_4428_mag1.copy({"code": "4428mag1b"})
        self.env["account.fiscal.position.account"].create(
            [
                {
                    "position_id": fiscal_position.id,
                    "account_src_id": src.id,
                    "account_dest_id": dest.id,
                }
                for src, dest in (
                    (self.account_371_mag1, account_371_alt),
                    (self.account_378_mag1, account_378_alt),
                    (self.account_4428_mag1, account_4428_alt),
                )
            ]
        )
        _po, move = self._do_purchase_receipt(
            self.warehouse_mag1, self.product_retail, 4, 50.0
        )
        extra_move = self.env["account.move"].search(
            [("l10n_ro_extra_stock_move_id", "=", move.id)]
        )
        markup = 4 * 50.0
        vat = 4 * 19.0
        self.assertEqual(
            self._lines_as_tuples(extra_move),
            sorted(
                [
                    (account_371_alt.id, markup, 0.0),
                    (account_378_alt.id, 0.0, markup),
                    (account_371_alt.id, vat, 0.0),
                    (account_4428_alt.id, 0.0, vat),
                ]
            ),
        )

    def test_price_included_mapping_does_not_change_the_split(self):
        """A shop whose fiscal position swaps the ordinary taxes for their
        price included variants prices the same shelf. The module reads the
        PVA as VAT inclusive whatever the tax says about itself, so only a
        change of rate can move the split - not a change of convention."""
        fiscal_position = self._make_retail_fiscal_position(self.warehouse_mag1)
        tax_19_incl = self.env["account.tax"].create(
            {
                "name": "TVA 19% inclus",
                "amount_type": "percent",
                "amount": 19.0,
                "type_tax_use": "sale",
                "price_include_override": "tax_included",
                "company_id": self.env.company.id,
                "fiscal_position_ids": [(6, 0, fiscal_position.ids)],
                "original_tax_ids": [(6, 0, self.tax_19.ids)],
            }
        )
        self.assertEqual(fiscal_position.map_tax(self.tax_19), tax_19_incl)
        prices = self.product_retail._l10n_ro_get_retail_prices(
            warehouse=self.warehouse_mag1
        )
        self.assertAlmostEqual(prices["price_without_vat"], 100.0, places=2)
        self.assertAlmostEqual(prices["vat"], 19.0, places=2)

    # -------------------------------------------------------------------
    # Only VAT belongs on 4428
    # -------------------------------------------------------------------
    def test_non_vat_sale_taxes_stay_out_of_the_retail_split(self):
        """A packaging deposit or an eco fee riding on the shop's taxes is
        neither markup nor deferred VAT: it is collected for somebody else.
        Splitting the shelf price with every tax pushed it onto 4428 as VAT
        that was never owed."""
        eco_tax = self.env["account.tax"].create(
            {
                "name": "Taxa verde 5%",
                "amount_type": "percent",
                "amount": 5.0,
                "type_tax_use": "sale",
                "company_id": self.env.company.id,
                "l10n_ro_retail_non_vat": True,
            }
        )
        self.assertFalse(eco_tax._l10n_ro_is_retail_vat())
        self.assertTrue(self.tax_19._l10n_ro_is_retail_vat())

        product = self.env["product.product"].create(
            {
                "name": "Produs cu taxa verde",
                "is_storable": True,
                "categ_id": self.product_retail.categ_id.id,
                "list_price": 124.0,  # 100 net + 19 VAT + 5 eco fee
                "standard_price": 50.0,
                "taxes_id": [(6, 0, (self.tax_19 | eco_tax).ids)],
            }
        )
        prices = product._l10n_ro_get_retail_prices(warehouse=self.warehouse_mag1)
        self.assertAlmostEqual(prices["price_without_vat"], 100.0, places=2)
        self.assertAlmostEqual(prices["vat"], 19.0, places=2)
        # The eco fee is not part of what the shop carries on 371 either.
        self.assertAlmostEqual(prices["price_with_vat"], 119.0, places=2)

    # -------------------------------------------------------------------
    # Returns reverse what was booked, sign included
    # -------------------------------------------------------------------
    def test_return_reverses_a_negative_markup(self):
        """A shop allowed to sell below cost carries a negative markup. The
        return of such a sale has to give the negative markup back, not book
        another release in the same direction: the absolute value looked
        equivalent and was, until the sign turned."""
        self.warehouse_mag1.l10n_ro_retail_allow_negative_markup = True
        self.env["product.pricelist.item"].with_context(
            skip_retail_price_change=True
        ).create(
            {
                "pricelist_id": self.pricelist_mag1.id,
                "applied_on": "0_product_variant",
                "product_id": self.product_retail.id,
                "compute_price": "fixed",
                "fixed_price": 35.7,  # 30 net and 5.70 VAT, against a cost of 50
            }
        )
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        markup, vat = self._carried(self.warehouse_mag1, self.product_retail)
        self.assertAlmostEqual(markup, -200.0, places=2)
        self.assertAlmostEqual(vat, 57.0, places=2)

        delivery = self._do_sale_delivery(
            self.warehouse_mag1, self.product_retail, 4, 35.7
        )
        markup, vat = self._carried(self.warehouse_mag1, self.product_retail)
        self.assertAlmostEqual(markup, -120.0, places=2)
        self.assertAlmostEqual(vat, 34.2, places=2)

        return_move = self._do_return(delivery.picking_id, 2)
        markup, vat = self._carried(self.warehouse_mag1, self.product_retail)
        # Eight units left in the shop, carrying eight units of markup.
        self.assertAlmostEqual(markup, -160.0, places=2)
        self.assertAlmostEqual(vat, 45.6, places=2)

        extra_move = self.env["account.move"].search(
            [("l10n_ro_extra_stock_move_id", "=", return_move.id)]
        )
        self.assertEqual(
            self._lines_as_tuples(extra_move),
            sorted(
                [
                    # Giving back a negative markup takes 371 down, not up.
                    (self.account_378_mag1.id, 40.0, 0.0),
                    (self.account_371_mag1.id, 0.0, 40.0),
                    (self.account_371_mag1.id, 11.4, 0.0),
                    (self.account_4428_mag1.id, 0.0, 11.4),
                ]
            ),
        )
