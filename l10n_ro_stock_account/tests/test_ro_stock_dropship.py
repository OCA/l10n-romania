# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import Form, tagged

from .common import TestROStockCommon


@tagged("post_install", "-at_install")
class TestROStockDropship(TestROStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dropship_route = cls.env.ref("stock_dropshipping.route_drop_shipping")
        cls.env["product.supplierinfo"].create(
            {
                "partner_id": cls.supplier_1.id,
                "product_tmpl_id": cls.product_fifo.product_tmpl_id.id,
                "price": 100.0,
            }
        )
        cls.env.user.group_ids += cls.env.ref("stock.group_adv_location")

    def _create_and_validate_dropship(self, qty=5.0):
        so_form = Form(self.env["sale.order"])
        so_form.partner_id = self.customer_1
        with so_form.order_line.new() as line:
            line.product_id = self.product_fifo
            line.product_uom_qty = qty
        so = so_form.save()
        so.order_line.write({"route_ids": [(6, 0, self.dropship_route.ids)]})
        so.action_confirm()

        po = self.env["purchase.order"].search(
            [("partner_id", "=", self.supplier_1.id), ("origin", "=", so.name)]
        )
        self.assertTrue(po, "A Purchase Order should be created for the dropship line")
        po.button_confirm()

        picking = po.picking_ids
        self.assertTrue(picking, "A dropship picking should be created")
        self.assertEqual(picking.picking_type_id.code, "dropship")

        picking.move_ids.quantity = qty
        picking.button_validate()
        self.assertEqual(picking.state, "done")

        return picking.move_ids

    def test_dropship_generates_valuation_entry(self):
        """A dropship delivery must credit the stock valuation account (371)
        and debit the expense account (607), symmetric with a regular
        delivery — instead of leaving the vendor bill's debit into 371
        uncompensated."""
        move = self._create_and_validate_dropship(qty=5.0)
        self.assertEqual(move.l10n_ro_move_type, "dropshipped")

        expected_value = move.purchase_line_id.price_unit * 5.0
        self.assertAlmostEqual(
            move.value,
            expected_value,
            places=2,
            msg="stock.move.value must be populated for a dropship move, "
            "not left at 0 as core stock_account leaves it",
        )

        self.assertTrue(
            move.account_move_id,
            "A dropship move must generate its own accounting entry",
        )
        lines = move.account_move_id.line_ids
        self.assertEqual(len(lines), 2)

        debit_line = lines.filtered(lambda line: line.debit > 0)
        credit_line = lines.filtered(lambda line: line.credit > 0)
        self.assertEqual(debit_line.account_id, self.account_expense)
        self.assertEqual(credit_line.account_id, self.account_valuation)
        self.assertAlmostEqual(debit_line.debit, expected_value, places=2)
        self.assertAlmostEqual(credit_line.credit, expected_value, places=2)

    def test_dropship_return_reverses_valuation_entry(self):
        """A dropship return move must storno the original entry: same
        accounts as a forward dropship move (debit expense / credit stock
        valuation), with the amount in red (negative), per the Romanian
        storno convention already used by "delivery_return"."""
        move = self._create_and_validate_dropship(qty=3.0)
        original_value = move.value

        return_wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=move.picking_id.id, active_model="stock.picking")
            .create({})
        )
        return_wizard.product_return_moves.quantity = 3.0
        return_picking = return_wizard._create_return()
        return_picking.move_ids.quantity = 3.0
        return_picking.button_validate()

        return_move = return_picking.move_ids
        self.assertEqual(return_move.l10n_ro_move_type, "dropshipped_return")
        self.assertTrue(
            return_move.account_move_id,
            "A dropship return move must generate its own accounting entry",
        )

        lines = return_move.account_move_id.line_ids
        expense_line = lines.filtered(
            lambda line: line.account_id == self.account_expense
        )
        valuation_line = lines.filtered(
            lambda line: line.account_id == self.account_valuation
        )
        self.assertTrue(expense_line and valuation_line)
        self.assertTrue(expense_line.is_storno)
        self.assertTrue(valuation_line.is_storno)
        self.assertAlmostEqual(expense_line.debit, -original_value, places=2)
        self.assertAlmostEqual(valuation_line.credit, -original_value, places=2)

    def test_dropship_does_not_affect_existing_fifo_stock_valuation(self):
        """Dropshipping a product that also has real FIFO stock elsewhere
        must not change that stock's quantity, value, or per-unit cost."""
        self._assert_dropship_does_not_affect_existing_stock_valuation(
            self.product_fifo
        )

    def test_dropship_does_not_affect_existing_average_stock_valuation(self):
        """Same as above, for an average-cost (AVCO) product.

        Core stock_account's own averaging engine
        (`product._run_average_batch`, see `stock_account/models/product.py`)
        folds any `is_dropship` move into the SAME moving-average pool as
        real purchases, by design — core's `_set_value()` adds the
        dropship's product to `products_to_recompute` (keyed on
        `is_dropship or is_in`) regardless of whether the move contributes
        any value there. Since Odoo 19 derives average-cost quant values
        live from `standard_price`, that recompute would retroactively
        reprice unrelated real stock of the same product just because it
        was also dropshipped. This module routes dropship moves around
        core's `_set_value()` entirely (see the `_set_value` override in
        `models/stock_move.py`) so they never reach that recompute."""
        self._assert_dropship_does_not_affect_existing_stock_valuation(self.product_avg)

    def _assert_dropship_does_not_affect_existing_stock_valuation(self, product):
        # Normal receipt into the company's own stock: 10 units @ 50.
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.supplier_1.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_qty": 10.0,
                            "price_unit": 50.0,
                        },
                    )
                ],
            }
        )
        po.button_confirm()
        receipt = po.picking_ids
        receipt.move_ids.quantity = 10.0
        receipt.button_validate()
        self.assertEqual(receipt.state, "done")

        quants_before = self.env["stock.quant"]._gather(
            product, receipt.location_dest_id
        )
        qty_before = sum(quants_before.mapped("quantity"))
        value_before = sum(quants_before.mapped("value"))
        standard_price_before = product.standard_price
        self.assertEqual(qty_before, 10.0)

        # Dropship the same product at a different (higher) unit cost, so any
        # bleed into the average cost would be detectable.
        so_form = Form(self.env["sale.order"])
        so_form.partner_id = self.customer_1
        with so_form.order_line.new() as line:
            line.product_id = product
            line.product_uom_qty = 4.0
        so = so_form.save()
        so.order_line.write({"route_ids": [(6, 0, self.dropship_route.ids)]})
        so.action_confirm()

        dropship_po = self.env["purchase.order"].search(
            [("partner_id", "=", self.supplier_1.id), ("origin", "=", so.name)]
        )
        self.assertTrue(dropship_po)
        dropship_po.order_line.price_unit = 80.0
        dropship_po.button_confirm()
        dropship_picking = dropship_po.picking_ids
        self.assertEqual(dropship_picking.picking_type_id.code, "dropship")
        dropship_picking.move_ids.quantity = 4.0
        dropship_picking.button_validate()

        dropship_move = dropship_picking.move_ids
        self.assertEqual(dropship_move.l10n_ro_move_type, "dropshipped")
        self.assertAlmostEqual(dropship_move.value, 80.0 * 4.0, places=2)

        quants_after = self.env["stock.quant"]._gather(
            product, receipt.location_dest_id
        )
        qty_after = sum(quants_after.mapped("quantity"))
        value_after = sum(quants_after.mapped("value"))

        self.assertEqual(
            qty_after,
            qty_before,
            "Dropshipping the same product must not change the real stock quantity",
        )
        self.assertAlmostEqual(
            value_after,
            value_before,
            places=2,
            msg="Dropshipping the same product must not change the real stock's value",
        )
        self.assertAlmostEqual(
            product.standard_price,
            standard_price_before,
            places=2,
            msg="Dropship cost must not bleed into the product's average cost",
        )
