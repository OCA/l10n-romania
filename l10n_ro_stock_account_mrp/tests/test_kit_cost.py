# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon


@tagged("post_install", "-at_install")
class TestROStockKitCost(TestROStockCommon):
    """Kit of 12 x ``product_fifo``. A customer return of a kit is linked to
    the kit sale line: ``sale_mrp`` prices it per kit unit (12 x 10 = 120),
    which used to become the cost of the component once the stock got
    empty."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.kit = cls.env["product.product"].create(
            {"name": "Kit 12 x FIFO", "type": "consu"}
        )
        cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.kit.product_tmpl_id.id,
                "product_qty": 1,
                "type": "phantom",
                "bom_line_ids": [
                    (0, 0, {"product_id": cls.product_fifo.id, "product_qty": 12})
                ],
            }
        )
        cls.product_fifo.standard_price = 10

    def _qty_on_hand(self):
        return self.product_fifo._with_valuation_context().qty_available

    def _update_stock(self, qty):
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": self.product_fifo.id,
                "location_id": self.location.id,
                "inventory_quantity": qty,
            }
        ).action_apply_inventory()

    def _sell_kits(self, qty):
        sale = self.env["sale.order"].create(
            {
                "partner_id": self.customer_1.id,
                "order_line": [
                    (0, 0, {"product_id": self.kit.id, "product_uom_qty": qty})
                ],
            }
        )
        sale.action_confirm()
        picking = sale.picking_ids
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.move_ids.picked = True
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        return picking

    def _return(self, picking, qty):
        return_wiz = self.env["stock.return.picking"].create({"picking_id": picking.id})
        return_wiz.product_return_moves.write({"quantity": qty})
        res = return_wiz.action_create_returns()
        return_pick = self.env["stock.picking"].browse(res["res_id"])
        return_pick.move_ids.quantity = qty
        return_pick.move_ids.picked = True
        return_pick.button_validate()
        self.assertEqual(return_pick.state, "done")
        return return_pick.move_ids

    def test_cost_after_kit_return_and_empty_stock(self):
        """Stock 24, sell 1 kit, return it, sell 2 kits: the stock is empty
        and the last incoming move is the kit return. The cost stays 10."""
        self._update_stock(24)
        delivery = self._sell_kits(1)
        self.assertAlmostEqual(self._qty_on_hand(), 12.0)

        return_move = self._return(delivery, 12)
        self.assertEqual(return_move.sale_line_id.product_id, self.kit)
        self.assertAlmostEqual(return_move.value, 120.0)
        self.assertAlmostEqual(self._qty_on_hand(), 24.0)

        self._sell_kits(2)
        self.assertAlmostEqual(self._qty_on_hand(), 0.0)
        last_in = self.product_fifo._get_last_in()
        self.assertEqual(last_in, return_move)
        self.assertAlmostEqual(last_in._get_price_unit(), 10.0)
        self.assertAlmostEqual(
            self.product_fifo.standard_price,
            10.0,
            msg="The cost of the component must not become the kit price",
        )

    def test_kit_price_unit_unchanged(self):
        """Outside of ``_get_last_in`` the component moves of a kit are still
        priced per kit unit (COGS of the kit)."""
        self._update_stock(24)
        delivery = self._sell_kits(2)
        self.assertAlmostEqual(delivery.move_ids._get_price_unit(), 120.0)
