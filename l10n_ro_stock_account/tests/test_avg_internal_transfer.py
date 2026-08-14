# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged

from .common import TestROStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestAVGInternalTransfer(TestROStockCommon):
    """An internal transfer must move the value of the source warehouse.

    The product is received at two different prices in two warehouses with
    different valuation accounts, so that the global average matches neither
    of them. Valuing the transfer at the global average would leave value
    behind in the source warehouse without any quantity to carry it.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Warehouse 2 already has its own valuation account (371001); give
        # warehouse 3 one too, so both ends of the transfer are identifiable
        # warehouses rather than the product's default account.
        cls.account_valuation_wh3 = cls.env.company.account_stock_valuation_id.copy(
            {"code": "371003"}
        )
        cls.location2.write(
            {
                "l10n_ro_property_stock_valuation_account_id": (
                    cls.account_valuation_wh3.id
                )
            }
        )

    def _receive(self, location, qty, price):
        self.test_case(
            {
                "steps": [
                    {
                        "type": "purchase",
                        "currency_id": self.env.company.currency_id,
                        "partner_id": self.supplier_1,
                        "product_id": self.product_avg,
                        "location": location,
                        "step": 1,
                        "qty": qty,
                        "stock_qty": qty,
                        "inv_qty": qty,
                        "price": price,
                        "inv_price": price,
                    }
                ]
            }
        )

    def _transfer(self, location_src, location_dest, qty):
        move = self.env["stock.move"].create(
            {
                "company_id": self.env.company.id,
                "location_id": location_src.id,
                "location_dest_id": location_dest.id,
                "product_id": self.product_avg.id,
                "product_uom": self.product_avg.uom_id.id,
                "product_uom_qty": qty,
            }
        )
        move._action_confirm()
        move._action_assign()
        move._set_quantity_done(qty)
        move.picked = True
        move._action_done()
        return move

    def test_internal_transfer_valued_at_source_warehouse_cost(self):
        self._receive(self.location1, 10.0, 40.0)
        self._receive(self.location2, 10.0, 60.0)

        # The global average is 50, which is the cost of neither warehouse.
        self.assertAlmostEqual(self.product_avg.standard_price, 50.0)

        move = self._transfer(self.location1, self.location2, 10.0)

        self.assertEqual(move.l10n_ro_move_type, "internal_transfer")
        # Without the fix the move is valued at the global average, 500.
        self.assertAlmostEqual(move.value, 400.0)

        # Both legs of the entry are built from that single value, so the
        # source warehouse is emptied of exactly what it held.
        account_move = move.account_move_id
        self.assertTrue(account_move)
        source_lines = account_move.line_ids.filtered(
            lambda line: line.account_id
            == self.location1.l10n_ro_property_stock_valuation_account_id
        )
        self.assertAlmostEqual(sum(source_lines.mapped("balance")), -400.0)

    def test_internal_transfer_without_source_account_keeps_standard_cost(self):
        """No valuation account on the source location: nothing changes.

        Source and destination then share the product's account, so there is
        no per-warehouse cost to follow and the standard behaviour applies.
        """
        self._receive(self.location, 10.0, 40.0)
        self._receive(self.location2, 10.0, 60.0)

        self.assertAlmostEqual(self.product_avg.standard_price, 50.0)
        self.assertFalse(
            self.location.l10n_ro_property_stock_valuation_account_id,
        )

        move = self._transfer(self.location, self.location2, 10.0)

        self.assertEqual(move.l10n_ro_move_type, "internal_transfer")
        self.assertAlmostEqual(move.value, 500.0)
