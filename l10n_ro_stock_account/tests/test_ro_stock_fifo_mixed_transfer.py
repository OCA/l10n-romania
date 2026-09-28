# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command


class FifoMixedTransferCases:
    """A transfer that mixes FIFO products with products costed otherwise must
    be validated as one transfer, with every line shipped.

    ``stock_move._action_done`` has to walk the per-location FIFO stack before
    anything is marked done, so it used to validate the non-FIFO moves on their
    own first and only then deal with the FIFO ones. That first call hands core
    a strict subset of the transfer's moves, and ``_create_backorder`` moves
    everything outside that subset - every FIFO move - into a fresh backorder,
    clearing ``picked`` on the way. The second call then looked for those moves
    behind core's ``moves_todo`` filter, which drops anything with ``picked``
    unset, and found nothing to do.

    The FIFO goods therefore never left the warehouse: the operator saw a
    validated transfer, the stock was never decreased, and the leftover
    backorder sat ``assigned`` with no quantity anybody would think to look at.
    Point of Sale made it worse - it validates its own transfer in the
    background, so a receipt mixing a FIFO product with a non-FIFO one simply
    did not decrease the stock, with nothing surfacing to the cashier.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.out_type = cls.location.warehouse_id.out_type_id

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _receive_product(self, product, qty, price, index):
        """Receive ``qty`` of ``product`` at ``price`` into ``self.location``."""
        self.create_purchase(
            {
                "currency_id": self.ron,
                "partner_id": self.supplier_1,
                "product_id": product,
                "qty": qty,
                "stock_qty": qty,
                "inv_qty": qty,
                "price": price,
                "inv_price": price,
                "index": index,
            }
        )

    def _mixed_qty_at_location(self, product):
        return product.with_context(
            location=self.location.id, strict=True
        ).qty_available

    def _make_mixed_delivery(self, qty):
        """A confirmed + reserved delivery carrying one FIFO and one non-FIFO
        line, both fully picked."""
        picking = self.env["stock.picking"].create(
            {
                "partner_id": self.customer_1.id,
                "picking_type_id": self.out_type.id,
                "location_id": self.location.id,
                "location_dest_id": self.customer_location.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "product_uom": product.uom_id.id,
                            "location_id": self.location.id,
                            "location_dest_id": self.customer_location.id,
                        }
                    )
                    for product in (self.product_fifo, self.product_avg)
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move._set_quantity_done(qty)
            move.picked = True
        return picking

    # ------------------------------------------------------------------
    # Scenarios
    # ------------------------------------------------------------------
    def test_mixed_transfer_ships_every_line_in_one_transfer(self):
        """Both lines leave the warehouse, and no backorder is spawned."""
        self._receive_product(self.product_fifo, 10, 100, "mixed_po_fifo")
        self._receive_product(self.product_avg, 10, 100, "mixed_po_avg")

        picking = self._make_mixed_delivery(4)
        picking.button_validate()
        self.env.invalidate_all()

        self.assertEqual(picking.state, "done", "The transfer itself must be validated")
        self.assertFalse(
            self.env["stock.picking"].search([("backorder_id", "=", picking.id)]),
            "Nothing was left behind, so no backorder may be created",
        )
        self.assertEqual(
            picking.move_ids.mapped("state"),
            ["done", "done"],
            "Both the FIFO and the non-FIFO move must be done",
        )
        self.assertAlmostEqual(
            self._mixed_qty_at_location(self.product_fifo),
            6.0,
            msg="The FIFO goods have to leave the location as well",
        )
        self.assertAlmostEqual(
            self._mixed_qty_at_location(self.product_avg),
            6.0,
            msg="The non-FIFO line keeps behaving as before",
        )

    def test_mixed_transfer_values_the_fifo_line_on_its_layer(self):
        """Shipping the two lines together must not disturb the FIFO valuation:
        the outgoing move is still valued by walking the per-location stack."""
        self._receive_product(self.product_fifo, 10, 100, "mixed_val_po_fifo")
        self._receive_product(self.product_avg, 10, 250, "mixed_val_po_avg")

        picking = self._make_mixed_delivery(4)
        picking.button_validate()
        self.env.invalidate_all()

        fifo_move = picking.move_ids.filtered(
            lambda move: move.product_id == self.product_fifo
        )
        self.assertAlmostEqual(
            fifo_move.value_manual,
            400.0,
            msg="4 units taken off the single 100/unit layer",
        )

    def test_mixed_transfer_still_backorders_what_is_not_picked(self):
        """The fix must not swallow genuine backorders: a line shipped short
        still leaves the remainder behind, which is core's normal workflow."""
        self._receive_product(self.product_fifo, 10, 100, "mixed_bo_po_fifo")
        self._receive_product(self.product_avg, 10, 100, "mixed_bo_po_avg")

        picking = self._make_mixed_delivery(4)
        fifo_move = picking.move_ids.filtered(
            lambda move: move.product_id == self.product_fifo
        )
        # Ship 1 of the 4 ordered FIFO units, leaving 3 to backorder.
        fifo_move._set_quantity_done(1)
        picking._action_done()
        self.env.invalidate_all()

        backorder = self.env["stock.picking"].search(
            [("backorder_id", "=", picking.id)]
        )
        self.assertTrue(backorder, "The unshipped remainder must still backorder")
        self.assertAlmostEqual(
            backorder.move_ids.product_uom_qty,
            3.0,
            msg="Only what was not shipped goes to the backorder",
        )
        self.assertAlmostEqual(
            self._mixed_qty_at_location(self.product_fifo),
            9.0,
            msg="Exactly what was picked left the location",
        )
