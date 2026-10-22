# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account_retail.tests.common import TestRetailCommon


@tagged("post_install", "-at_install")
class TestRetailPriceDifference(TestRetailCommon):
    def _make_item(self, move, value_diff):
        wizard = self.env["l10n_ro.price_difference_confirm_dialog"].create(
            {"invoice_id": False}
        )
        return self.env["l10n_ro.price_difference_item"].create(
            {
                "confirmation_id": wizard.id,
                "stock_move_id": move.id,
                "product_id": move.product_id.id,
                "value_diff": value_diff,
                "qty_diff": 0.0,
            }
        )

    def test_wizard_shows_the_markup_left_after_the_difference(self):
        """The dialog answers the question the user actually has: is there
        still a markup after this bill, or is a price change due first?"""
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        move = self.env["stock.move"].search(
            [
                ("product_id", "=", self.product_retail.id),
                ("location_dest_id", "=", self.loc_mag1.id),
                ("state", "=", "done"),
            ],
            limit=1,
        )
        item = self._make_item(move, 100.0)
        self.assertEqual(item.l10n_ro_retail_warehouse_id, self.warehouse_mag1)
        self.assertAlmostEqual(item.l10n_ro_retail_markup, 500.0, places=2)
        self.assertAlmostEqual(item.l10n_ro_retail_markup_after, 400.0, places=2)
        self.assertEqual(item.l10n_ro_retail_covered, "ok")

    def test_wizard_flags_a_difference_that_eats_the_markup(self):
        self._set_initial_stock(self.loc_mag1, self.product_retail, 10)
        move = self.env["stock.move"].search(
            [
                ("product_id", "=", self.product_retail.id),
                ("location_dest_id", "=", self.loc_mag1.id),
                ("state", "=", "done"),
            ],
            limit=1,
        )
        item = self._make_item(move, 900.0)
        self.assertEqual(item.l10n_ro_retail_covered, "short")
        self.assertAlmostEqual(item.l10n_ro_retail_markup_after, -400.0, places=2)

    def test_wizard_is_quiet_outside_a_shop(self):
        self._set_initial_stock(self.location, self.product_retail, 10)
        move = self.env["stock.move"].search(
            [
                ("product_id", "=", self.product_retail.id),
                ("location_dest_id", "=", self.location.id),
                ("state", "=", "done"),
            ],
            limit=1,
        )
        item = self._make_item(move, 100.0)
        self.assertEqual(item.l10n_ro_retail_covered, "na")
        self.assertFalse(item.l10n_ro_retail_warehouse_id)
