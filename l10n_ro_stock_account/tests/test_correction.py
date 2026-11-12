# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockCorrection(TestStockCommon):
    """Correcting the quantity of an already done move line must create the
    valuation layer, so the value of the stock follows the quantity."""

    def _reception_move_line(self):
        move_line = self.env["stock.move.line"].search(
            [
                ("product_id", "=", self.product_1.id),
                ("state", "=", "done"),
                ("location_id.usage", "=", "supplier"),
            ],
            limit=1,
        )
        self.assertTrue(move_line, "No done reception move line found")
        return move_line

    def _new_layers(self, move, layers_before):
        move.invalidate_recordset(["stock_valuation_layer_ids"])
        return move.sudo().stock_valuation_layer_ids - layers_before

    def test_valued_type_of_reception(self):
        self.make_purchase()
        move = self._reception_move_line().move_id
        self.assertEqual(move._l10n_ro_get_valued_type(), "reception")

    def test_correction_increase_quantity(self):
        self.make_purchase()
        move_line = self._reception_move_line()
        move = move_line.move_id
        layers_before = move.sudo().stock_valuation_layer_ids

        move_line.write({"quantity": move_line.quantity + 2})
        new_layers = self._new_layers(move, layers_before)

        self.assertTrue(new_layers, "No valuation layer created for the correction")
        self.assertEqual(set(new_layers.mapped("l10n_ro_valued_type")), {"reception"})
        self.assertEqual(new_layers.l10n_ro_account_id, self.account_valuation)
        self.assertAlmostEqual(sum(new_layers.mapped("quantity")), 2.0)
        self.assertAlmostEqual(sum(new_layers.mapped("value")), 2 * self.price_p1)

        val_stock_p1 = round((self.qty_po_p1 + 2) * self.price_p1, 2)
        val_stock_p2 = round(self.qty_po_p2 * self.price_p2, 2)
        self.check_stock_valuation(val_stock_p1, val_stock_p2)

    def test_correction_decrease_quantity(self):
        self.make_purchase()
        move_line = self._reception_move_line()
        move = move_line.move_id
        layers_before = move.sudo().stock_valuation_layer_ids

        move_line.write({"quantity": move_line.quantity - 2})
        new_layers = self._new_layers(move, layers_before)

        self.assertTrue(new_layers, "No valuation layer created for the correction")
        self.assertAlmostEqual(sum(new_layers.mapped("quantity")), -2.0)
        self.assertAlmostEqual(sum(new_layers.mapped("value")), -2 * self.price_p1)

        val_stock_p1 = round((self.qty_po_p1 - 2) * self.price_p1, 2)
        val_stock_p2 = round(self.qty_po_p2 * self.price_p2, 2)
        self.check_stock_valuation(val_stock_p1, val_stock_p2)

    def test_correction_on_delivery_posts_entry(self):
        """On a delivery the correction must also post the stock entry,
        because in Romania the delivery is what discharges the stock."""
        self.make_purchase()
        self.create_so()
        move_line = self.env["stock.move.line"].search(
            [
                ("product_id", "=", self.product_1.id),
                ("state", "=", "done"),
                ("location_dest_id.usage", "=", "customer"),
            ],
            limit=1,
        )
        self.assertTrue(move_line, "No done delivery move line found")
        move = move_line.move_id
        self.assertEqual(move._l10n_ro_get_valued_type(), "delivery")
        layers_before = move.sudo().stock_valuation_layer_ids

        move_line.write({"quantity": move_line.quantity + 1})
        new_layers = self._new_layers(move, layers_before)

        self.assertTrue(new_layers, "No valuation layer created for the correction")
        self.assertEqual(set(new_layers.mapped("l10n_ro_valued_type")), {"delivery"})
        self.assertTrue(
            new_layers.mapped("account_move_id"),
            "No accounting entry for the delivery correction",
        )
