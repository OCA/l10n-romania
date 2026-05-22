# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

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
