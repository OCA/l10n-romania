# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account_retail.tests.common import TestRetailCommon


@tagged("post_install", "-at_install")
class TestRetailLandedCost(TestRetailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.landed_cost_product = cls.env["product.product"].create(
            {
                "name": "Transport",
                "type": "service",
                "is_storable": False,
                "landed_cost_ok": True,
                "standard_price": 0.0,
            }
        )

    def _make_landed_cost(self, picking, amount):
        cost = self.env["stock.landed.cost"].create(
            {
                "company_id": self.env.company.id,
                "picking_ids": [(6, 0, picking.ids)],
                "account_journal_id": self.env.company.account_stock_journal_id.id,
                "cost_lines": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.landed_cost_product.id,
                            "price_unit": amount,
                            "split_method": "equal",
                            "account_id": self.account_expense.id,
                        },
                    )
                ],
            }
        )
        cost.compute_landed_cost()
        return cost

    def _carried(self, warehouse, product):
        return self.env["l10n.ro.retail.markup.line"]._l10n_ro_carried(
            warehouse, product, self.env.company
        )

    def test_landed_cost_leaves_371_at_shelf_price(self):
        """A landed cost on goods in a shop must not move 371.

        The shelf price has not changed, so the value the shop carries has not
        changed either: what changes is the split. The cost goes up by the
        landed amount and the markup goes down by the same amount.
        """
        _po, move = self._do_purchase_receipt(
            self.warehouse_mag1, self.product_retail, 10, 50.0
        )
        markup_before, vat_before = self._carried(
            self.warehouse_mag1, self.product_retail
        )
        self.assertAlmostEqual(markup_before, 500.0, places=2)  # 10 * 50

        cost = self._make_landed_cost(move.picking_id, 100.0)
        cost.button_validate()

        markup_after, vat_after = self._carried(
            self.warehouse_mag1, self.product_retail
        )
        self.assertAlmostEqual(markup_after, 400.0, places=2)
        self.assertAlmostEqual(vat_after, vat_before, places=2)

        correction = cost.l10n_ro_retail_markup_line_ids
        self.assertTrue(correction, "No markup correction recorded")
        self.assertAlmostEqual(sum(correction.mapped("markup")), -100.0, places=2)
        self.assertEqual(correction.origin_type, "landed_cost")

        entry = correction.account_move_id
        self.assertTrue(entry, "No markup correction entry posted")
        self.assertEqual(
            sorted(
                (line.account_id.id, round(line.debit, 2), round(line.credit, 2))
                for line in entry.line_ids
            ),
            sorted(
                [
                    (self.account_378_mag1.id, 100.0, 0.0),
                    (self.account_371_mag1.id, 0.0, 100.0),
                ]
            ),
        )

    def test_landed_cost_beyond_the_markup_is_refused(self):
        """A landed cost bigger than the markup would leave the goods costing
        more than they are priced at, so it is refused with the shortfall."""
        _po, move = self._do_purchase_receipt(
            self.warehouse_mag1, self.product_retail, 10, 50.0
        )
        cost = self._make_landed_cost(move.picking_id, 900.0)
        with self.assertRaises(UserError):
            cost.button_validate()

    def test_landed_cost_beyond_the_markup_allowed_when_warehouse_permits(self):
        """A shop that sells below cost on purpose takes the negative markup."""
        self.warehouse_mag1.l10n_ro_retail_allow_negative_markup = True
        _po, move = self._do_purchase_receipt(
            self.warehouse_mag1, self.product_retail, 10, 50.0
        )
        cost = self._make_landed_cost(move.picking_id, 900.0)
        cost.button_validate()
        markup, _vat = self._carried(self.warehouse_mag1, self.product_retail)
        self.assertAlmostEqual(markup, -400.0, places=2)  # 500 - 900

    def test_landed_cost_outside_a_shop_is_left_alone(self):
        """Goods in a plain warehouse are valued at cost: nothing to rebalance."""
        _po, move = self._do_purchase_receipt(
            self.location.warehouse_id, self.product_retail, 10, 50.0
        )
        cost = self._make_landed_cost(move.picking_id, 100.0)
        cost.button_validate()
        self.assertFalse(cost.l10n_ro_retail_markup_line_ids)
