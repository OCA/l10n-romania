# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestInternalTransferValue(TestStockCommon):
    """Internal transfer between two valuation accounts (gestiuni).

    A transfer neither creates nor destroys value: it has to take out of the
    source account exactly what that account holds for the transferred goods,
    and put the same amount into the destination account.
    """

    def _receive(self, product, qty, price, location):
        """Receive `qty` of `product` at `price` straight into `location`."""
        picking_type = self.picking_type_in_warehouse
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": location.id,
            }
        )
        self.env["stock.move"].create(
            {
                "name": product.name,
                "product_id": product.id,
                "product_uom_qty": qty,
                "product_uom": product.uom_id.id,
                "picking_id": picking.id,
                "price_unit": price,
                "location_id": picking.location_id.id,
                "location_dest_id": location.id,
            }
        )
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move._set_quantity_done(qty)
        picking.button_validate()
        picking._action_done()
        return picking

    def _valuation_on_account(self, product, account):
        """Quantity and value the given valuation account holds."""
        groups = self.env["stock.valuation.layer"]._read_group(
            [
                ("product_id", "=", product.id),
                ("l10n_ro_account_id", "=", account.id),
            ],
            aggregates=["quantity:sum", "value:sum"],
        )
        if not groups:
            return 0.0, 0.0
        quantity, value = groups[0]
        return quantity, round(value, 2)

    def _setup_two_accounts(self):
        """Two accounts holding the same product at different costs.

        The global average cost (50) then matches neither of the two accounts
        (40 and 60).
        """
        product = self.product_2
        self.assertEqual(product.cost_method, "average")
        self.assertTrue(product.categ_id.l10n_ro_stock_account_change)
        self.location_warehouse.l10n_ro_property_stock_valuation_account_id = (
            self.account_valuation
        )
        self.location_warehouse_other.l10n_ro_property_stock_valuation_account_id = (
            self.account_valuation_mp
        )
        self._receive(product, 10, 40.0, self.location_warehouse)
        self._receive(product, 10, 60.0, self.location_warehouse_other)
        self.assertAlmostEqual(product.standard_price, 50.0, 2)
        return product

    def test_internal_transfer_inside_the_same_account(self):
        """A transfer that does not leave its account must be value neutral.

        Such a transfer gets no accounting entry (source and destination
        account are the same), so an imbalance between the two legs is pure
        drift between the per account valuation and the trial balance.
        """
        product = self._setup_two_accounts()
        account = self.account_valuation
        before = self._valuation_on_account(product, account)

        self.transfer(self.location_warehouse, self.location_warehouse, product=product)
        svls = self.picking.move_ids.stock_valuation_layer_ids.filtered(
            lambda svl: svl.l10n_ro_valued_type == "internal_transfer"
        )
        self.assertEqual(len(svls), 2)
        self.assertAlmostEqual(sum(svls.mapped("value")), 0.0, 2)
        self.assertEqual(svls.mapped("l10n_ro_account_id"), account)
        self.assertEqual(self._valuation_on_account(product, account), before)
        # Both legs are valued at what the account holds (40), not at the
        # global average cost of the product (50).
        for svl in svls:
            self.assertAlmostEqual(svl.unit_cost, 40.0, 2)

    def test_internal_transfer_legs_are_equal_and_at_source_cost(self):
        """The two legs must be equal and valued at the source account cost.

        The out leg used to be valued at ``product.standard_price``, i.e. the
        average cost over ALL the valuation accounts of the product. When the
        source account holds the goods at a different cost, the transfer takes
        out more (or less) than that account owns and leaves it with value and
        no quantity, while the accounting entry follows the wrong leg.
        """
        product = self._setup_two_accounts()
        account_src = self.account_valuation
        account_dest = self.account_valuation_mp
        self.assertEqual(
            self._valuation_on_account(product, account_src), (10.0, 400.0)
        )
        self.assertEqual(
            self._valuation_on_account(product, account_dest), (10.0, 600.0)
        )

        # Transfer 2 pieces from the source account to the destination one.
        self.transfer(
            self.location_warehouse, self.location_warehouse_other, product=product
        )
        move = self.picking.move_ids
        svls = move.stock_valuation_layer_ids.filtered(
            lambda svl: svl.l10n_ro_valued_type == "internal_transfer"
        )
        self.assertEqual(len(svls), 2, "An internal transfer has exactly two legs")
        out_svl = svls.filtered(lambda svl: svl.quantity < 0)
        in_svl = svls.filtered(lambda svl: svl.quantity > 0)
        self.assertEqual(out_svl.l10n_ro_account_id, account_src)
        self.assertEqual(in_svl.l10n_ro_account_id, account_dest)

        # A transfer neither creates nor destroys value.
        self.assertAlmostEqual(
            abs(out_svl.value),
            in_svl.value,
            2,
            "The two legs of an internal transfer must be equal in absolute value",
        )
        # It takes out of the source account what that account holds (40),
        # not the global average cost of the product (50).
        self.assertAlmostEqual(out_svl.unit_cost, 40.0, 2)
        self.assertAlmostEqual(abs(out_svl.value), 80.0, 2)
        self.assertAlmostEqual(in_svl.unit_cost, 40.0, 2)

        # No value left behind without quantity on the source account.
        self.assertEqual(self._valuation_on_account(product, account_src), (8.0, 320.0))
        self.assertEqual(
            self._valuation_on_account(product, account_dest), (12.0, 680.0)
        )

        # The accounting entry follows the out leg, so it moves the same amount.
        self.assertTrue(out_svl.account_move_id)
        aml = out_svl.account_move_id.line_ids
        self.assertAlmostEqual(
            sum(aml.filtered(lambda ln: ln.account_id == account_dest).mapped("debit")),
            80.0,
            2,
        )
        self.assertAlmostEqual(
            sum(aml.filtered(lambda ln: ln.account_id == account_src).mapped("credit")),
            80.0,
            2,
        )
