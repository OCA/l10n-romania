# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockRevaluation(TestStockCommon):
    """Valuation layers created outside of a stock move must still carry the
    Romanian valuation account, otherwise the stock reports - which group on
    `l10n_ro_account_id` - cannot be reconciled with the trial balance."""

    def test_change_standard_price_sets_valuation_account(self):
        self.make_purchase()
        product = self.product_2
        self.assertEqual(product.cost_method, "average")

        layers = self.env["stock.valuation.layer"]
        layers_before = layers.search([("product_id", "=", product.id)])
        product.with_company(self.env.company).standard_price = self.price_p2 + 10
        new_layers = layers.search([("product_id", "=", product.id)]) - layers_before

        self.assertTrue(new_layers, "No valuation layer for the cost change")
        self.assertFalse(new_layers.stock_move_id)
        self.assertEqual(new_layers.l10n_ro_account_id, self.account_valuation)

    def test_layer_without_valued_type_does_not_break(self):
        """`_compute_account` used to raise on an empty `l10n_ro_valued_type`.

        The branch that reads the valued type is only reached when the layer
        has an accounting entry, so a delivery layer is needed: in Romania a
        reception does not post an entry in the stock journal, the stock is
        charged from the vendor bill.
        """
        self.make_purchase()
        self.create_so()
        layer = self.env["stock.valuation.layer"].search(
            [
                ("product_id", "=", self.product_1.id),
                ("l10n_ro_valued_type", "=", "delivery"),
                ("account_move_id", "!=", False),
            ],
            limit=1,
        )
        self.assertTrue(layer, "No delivery layer with an accounting entry")
        layer.l10n_ro_valued_type = False
        layer._compute_account()
        self.assertTrue(layer.l10n_ro_account_id)
