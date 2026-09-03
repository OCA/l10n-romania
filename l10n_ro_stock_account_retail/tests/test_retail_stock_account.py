# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon


@tagged("post_install", "-at_install")
class TestRetailStockAccount(TestROStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        Account = cls.env["account.account"]
        cls.account_371 = company.account_stock_valuation_id
        cls.account_378 = Account.create(
            {
                "code": "378ret",
                "name": "Diferente de pret la marfuri (test)",
                "account_type": "asset_current",
                "company_ids": [(4, company.id)],
            }
        )
        cls.account_4428 = Account.create(
            {
                "code": "4428ret",
                "name": "TVA neexigibila (test)",
                "account_type": "liability_current",
                "company_ids": [(4, company.id)],
            }
        )
        company.l10n_ro_account_markup_id = cls.account_378
        company.l10n_ro_account_deferred_vat_id = cls.account_4428
        cls.tax_19 = cls.env["account.tax"].create(
            {
                "name": "TVA 19% retail",
                "amount_type": "percent",
                "amount": 19.0,
                "type_tax_use": "sale",
                "company_id": company.id,
            }
        )
        cls.retail_pricelist = cls.env["product.pricelist"].create(
            {
                "name": "Retail pricelist",
                "currency_id": company.currency_id.id,
                "company_id": company.id,
            }
        )
        cls.retail_warehouse = cls.env["stock.warehouse"].create(
            {
                "name": "Magazin",
                "code": "MAG",
                "l10n_ro_retail": True,
                "l10n_ro_retail_pricelist_id": cls.retail_pricelist.id,
            }
        )
        cls.retail_stock_loc = cls.retail_warehouse.lot_stock_id
        cls.product_retail = cls.env["product.product"].create(
            {
                "name": "Produs Magazin",
                "is_storable": True,
                "categ_id": cls.category_marfa_avg.id,
                "list_price": 100.0,
                "standard_price": 50.0,
                "taxes_id": [(6, 0, cls.tax_19.ids)],
            }
        )

        # --- Two fully-configured retail stores (mirrors a real multi-shop
        # setup: each store has its own 371/607 valuation accounts and its
        # own 378/4428 markup accounts), used to test transfers between
        # a non-retail depot and retail stores, and between two stores. ---
        cls.account_482 = Account.create(
            {
                "code": "482test",
                "name": "Decontari intre gestiuni (test)",
                "account_type": "asset_current",
                "company_ids": [(4, company.id)],
            }
        )
        company.l10n_ro_property_stock_transfer_account_id = cls.account_482

        cls.pricelist_mag1 = cls.env["product.pricelist"].create(
            {
                "name": "Retail pricelist MAG1",
                "currency_id": company.currency_id.id,
                "company_id": company.id,
            }
        )
        cls.warehouse_mag1 = cls.env["stock.warehouse"].create(
            {
                "name": "Magazin 1",
                "code": "MAG1",
                "l10n_ro_retail": True,
                "l10n_ro_retail_pricelist_id": cls.pricelist_mag1.id,
            }
        )
        cls.loc_mag1 = cls.warehouse_mag1.lot_stock_id
        cls.account_371_mag1 = cls.account_371.copy({"code": "371mag1"})
        cls.account_607_mag1 = cls.account_expense.copy({"code": "607mag1"})
        cls.account_378_mag1 = Account.create(
            {
                "code": "378mag1",
                "name": "Adaos comercial MAG1 (test)",
                "account_type": "asset_current",
                "company_ids": [(4, company.id)],
            }
        )
        cls.account_4428_mag1 = Account.create(
            {
                "code": "4428mag1",
                "name": "TVA neexigibila MAG1 (test)",
                "account_type": "liability_current",
                "company_ids": [(4, company.id)],
            }
        )
        cls.loc_mag1.write(
            {
                "l10n_ro_property_stock_valuation_account_id": (
                    cls.account_371_mag1.id
                ),
                "l10n_ro_property_account_expense_location_id": (
                    cls.account_607_mag1.id
                ),
                "l10n_ro_account_markup_id": cls.account_378_mag1.id,
                "l10n_ro_account_deferred_vat_id": cls.account_4428_mag1.id,
            }
        )

        cls.pricelist_mag2 = cls.env["product.pricelist"].create(
            {
                "name": "Retail pricelist MAG2",
                "currency_id": company.currency_id.id,
                "company_id": company.id,
            }
        )
        cls.warehouse_mag2 = cls.env["stock.warehouse"].create(
            {
                "name": "Magazin 2",
                "code": "MAG2",
                "l10n_ro_retail": True,
                "l10n_ro_retail_pricelist_id": cls.pricelist_mag2.id,
            }
        )
        cls.loc_mag2 = cls.warehouse_mag2.lot_stock_id
        cls.account_371_mag2 = cls.account_371.copy({"code": "371mag2"})
        cls.account_607_mag2 = cls.account_expense.copy({"code": "607mag2"})
        cls.account_378_mag2 = Account.create(
            {
                "code": "378mag2",
                "name": "Adaos comercial MAG2 (test)",
                "account_type": "asset_current",
                "company_ids": [(4, company.id)],
            }
        )
        cls.account_4428_mag2 = Account.create(
            {
                "code": "4428mag2",
                "name": "TVA neexigibila MAG2 (test)",
                "account_type": "liability_current",
                "company_ids": [(4, company.id)],
            }
        )
        cls.loc_mag2.write(
            {
                "l10n_ro_property_stock_valuation_account_id": (
                    cls.account_371_mag2.id
                ),
                "l10n_ro_property_account_expense_location_id": (
                    cls.account_607_mag2.id
                ),
                "l10n_ro_account_markup_id": cls.account_378_mag2.id,
                "l10n_ro_account_deferred_vat_id": cls.account_4428_mag2.id,
            }
        )

    def test_location_inherits_retail_flag(self):
        self.assertTrue(self.retail_stock_loc.l10n_ro_retail)
        self.retail_warehouse.l10n_ro_retail = False
        self.retail_stock_loc.invalidate_recordset()
        self.assertFalse(self.retail_stock_loc.l10n_ro_retail)

    def test_retail_price_split(self):
        prices = self.product_retail.product_tmpl_id._l10n_ro_get_retail_prices(
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
    def _set_initial_stock(self, location, product, qty):
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": product.id,
                "location_id": location.id,
                "inventory_quantity": qty,
            }
        ).action_apply_inventory()

    def _do_transfer(self, src_location, dest_location, product, qty):
        picking_type = src_location.warehouse_id.int_type_id
        move = self.env["stock.move"].create(
            {
                "company_id": self.env.company.id,
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": qty,
                "location_id": src_location.id,
                "location_dest_id": dest_location.id,
                "picking_type_id": picking_type.id,
            }
        )
        move._action_confirm()
        move._action_assign()
        move._set_quantity_done(qty)
        move.picked = True
        move._action_done()
        return move

    def _lines_as_tuples(self, move):
        """(account_id, debit, credit) tuples for a posted account.move,
        rounded and sorted so the comparison is order-independent."""
        return sorted(
            (line.account_id.id, round(line.debit, 2), round(line.credit, 2))
            for line in move.line_ids
        )

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
    def _do_purchase_receipt(self, warehouse, product, qty, price_unit):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.supplier_1.id,
                "picking_type_id": warehouse.in_type_id.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_qty": qty,
                            "price_unit": price_unit,
                        },
                    )
                ],
            }
        )
        po.button_confirm()
        picking = po.picking_ids
        picking.move_ids._set_quantity_done(qty)
        picking.move_ids.picked = True
        picking.button_validate()
        return po, picking.move_ids

    def _do_sale_delivery(self, warehouse, product, qty, price_unit, discount=0.0):
        so = self.env["sale.order"].create(
            {
                "partner_id": self.customer_1.id,
                "warehouse_id": warehouse.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "price_unit": price_unit,
                            "discount": discount,
                        },
                    )
                ],
            }
        )
        so.action_confirm()
        picking = so.picking_ids
        picking.move_ids._set_quantity_done(qty)
        picking.move_ids.picked = True
        picking.button_validate()
        return picking.move_ids

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
    def _do_return(self, picking, qty):
        return_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=[picking.id],
                active_id=picking.id,
                active_model="stock.picking",
            )
        )
        return_wiz = return_form.save()
        return_wiz.product_return_moves.write({"quantity": qty, "to_refund": True})
        res = return_wiz.action_create_returns()
        return_picking = self.env["stock.picking"].browse(res["res_id"])
        return_picking.action_confirm()
        return_picking.action_assign()
        return_picking.move_ids._set_quantity_done(qty)
        return_picking.move_ids.picked = True
        return_picking._action_done()
        return return_picking.move_ids

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
    # Retail price change (Proces Verbal de Schimbare Pret)
    # -------------------------------------------------------------------
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
                "fixed_price": 80.0,
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
        self.assertAlmostEqual(line.old_price_with_vat, 119.0, places=2)  # 100*1.19
        self.assertAlmostEqual(line.new_price_with_vat, 154.7, places=2)  # 130*1.19
