from odoo.tests.common import TransactionCase


class TestStockMoveSecondAccount(TransactionCase):
    def setUp(self):
        super().setUp()

        self.Account = self.env["account.account"]
        self.Location = self.env["stock.location"]
        self.Move = self.env["stock.move"]
        self.Product = self.env["product.product"]

        self.account = self.Account.create(
            {
                "name": "Test Valuation",
                "code": "X12345",
                "account_type": "asset_current",
            }
        )

        self.loc_internal_1 = self.Location.create(
            {
                "name": "Internal 1",
                "usage": "internal",
                "l10n_ro_property_stock_valuation_account_id": self.account.id,
            }
        )

        self.loc_internal_2 = self.Location.create(
            {
                "name": "Internal 2",
                "usage": "internal",
            }
        )

        self.loc_customer = self.Location.create(
            {
                "name": "Customer",
                "usage": "customer",
            }
        )

        self.product = self.Product.create(
            {
                "name": "Test Product",
                "type": "consu",
            }
        )

    def test_internal_to_internal_sets_account(self):
        move = self.Move.create(
            {
                "product_id": self.product.id,
                "product_uom_qty": 1,
                "product_uom": self.product.uom_id.id,
                "location_id": self.loc_internal_1.id,
                "location_dest_id": self.loc_internal_2.id,
            }
        )

        self.assertEqual(
            move.l10n_ro_second_account_id,
            self.account,
        )

    def test_internal_to_customer_sets_false(self):
        move = self.Move.create(
            {
                "product_id": self.product.id,
                "product_uom_qty": 1,
                "product_uom": self.product.uom_id.id,
                "location_id": self.loc_internal_1.id,
                "location_dest_id": self.loc_customer.id,
            }
        )

        self.assertFalse(
            move.l10n_ro_second_account_id,
        )
