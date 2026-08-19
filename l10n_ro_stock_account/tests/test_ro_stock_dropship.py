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
