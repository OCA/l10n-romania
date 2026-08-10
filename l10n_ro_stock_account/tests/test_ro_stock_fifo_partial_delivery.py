# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from .common import TestROStockCommon


@tagged("post_install", "-at_install")
class TestROStockFifoPartialDelivery(TestROStockCommon):
    """``stock_move._split_for_fifo_assignment`` must walk the per-location FIFO
    stack for ``move.quantity`` - what is actually being shipped on this
    transfer - and not for ``product_uom_qty``/``product_qty``, the *ordered*
    demand.

    Shipping less than ordered (lowering ``quantity`` so the rest backorders)
    is the normal Odoo workflow: core's own ``_create_backorder`` compares
    ``quantity`` against ``product_uom_qty`` for exactly that decision, so
    ``product_uom_qty`` is supposed to stay at the full order.

    Walking the stack for the ordered demand meant that as soon as satisfying
    that (inflated) target needed more than one price layer, the split created
    an extra ``stock.move`` for the difference and shipped it too: the full
    original demand went out regardless of what was picked, with no backorder.
    With a single layer covering the order the bug was silent - the same
    quantity left, only mis-valued."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.out_type = cls.location.warehouse_id.out_type_id

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _receive(self, qty, price, index):
        """Receive ``qty`` at ``price`` into ``self.location``, one FIFO layer."""
        self.create_purchase(
            {
                "currency_id": self.ron,
                "partner_id": self.supplier_1,
                "product_id": self.product_fifo,
                "qty": qty,
                "stock_qty": qty,
                "inv_qty": qty,
                "price": price,
                "inv_price": price,
                "index": index,
            }
        )
        return self.env["stock.move"].search(
            [
                ("product_id", "=", self.product_fifo.id),
                ("is_in", "=", True),
                ("state", "=", "done"),
                ("location_dest_id", "=", self.location.id),
            ],
            order="id desc",
            limit=1,
        )

    def _two_layers(self):
        """10 @ 100 then 10 @ 150 - two layers, so a split is needed as soon as
        more than 10 units are shipped. Returns the two incoming moves."""
        first = self._receive(10, 100, "pd_po1")
        second = self._receive(10, 150, "pd_po2")
        self.assertAlmostEqual(self._qty_at_location(), 20.0)
        # Guard the fixture itself: the stack must be ordered oldest first,
        # otherwise the value assertions below would be checking the wrong
        # thing rather than the split.
        layers = self.product_fifo.with_context(
            location=self.location.ids
        )._run_fifo_layers(20, location=self.location)
        self.assertEqual(
            [(layer["move_id"], layer["quantity"], layer["value"]) for layer in layers],
            [(first.id, 10.0, 1000.0), (second.id, 10.0, 1500.0)],
        )
        return first, second

    def _qty_at_location(self):
        return self.product_fifo.with_context(
            location=self.location.id, strict=True
        ).qty_available

    def _make_delivery(self, ordered_qty):
        """A confirmed + reserved delivery for ``ordered_qty``."""
        picking = self.env["stock.picking"].create(
            {
                "partner_id": self.customer_1.id,
                "picking_type_id": self.out_type.id,
                "location_id": self.location.id,
                "location_dest_id": self.customer_location.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product_fifo.id,
                            "product_uom_qty": ordered_qty,
                            "product_uom": self.product_fifo.uom_id.id,
                            "location_id": self.location.id,
                            "location_dest_id": self.customer_location.id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        return picking

    def _pick_and_validate(self, picking, picked_qty, expect_backorder):
        """Ship ``picked_qty`` out of the picking's demand, going through the
        backorder wizard the same way the user does."""
        picking.move_ids._set_quantity_done(picked_qty)
        picking.move_ids.picked = True
        action = picking.button_validate()
        if expect_backorder:
            self.assertIsInstance(
                action,
                dict,
                "Shipping less than ordered must ask about the backorder",
            )
            self.assertEqual(action["res_model"], "stock.backorder.confirmation")
            wizard = Form(
                self.env[action["res_model"]].with_context(**action["context"])
            ).save()
            wizard.process()
        else:
            self.assertIs(
                action, True, "A fully picked transfer must validate directly"
            )
        self.assertEqual(picking.state, "done")
        return picking

    def _done_moves(self, picking):
        return picking.move_ids.filtered(
            lambda m: m.product_id == self.product_fifo and m.state == "done"
        )

    def _backorder_of(self, picking):
        return self.env["stock.picking"].search([("backorder_id", "=", picking.id)])

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_partial_pick_ships_only_what_was_picked(self):
        """The regression itself: 15 ordered, only 5 picked, two layers on the
        stack. The 5 picked must go out - valued on the oldest layer - and the
        remaining 10 must land in a backorder."""
        self._two_layers()
        picking = self._make_delivery(15)
        self._pick_and_validate(picking, 5, expect_backorder=True)

        done_moves = self._done_moves(picking)
        self.assertAlmostEqual(
            sum(done_moves.mapped("quantity")),
            5.0,
            msg="Only the picked quantity may be shipped, not the full demand",
        )
        self.assertEqual(
            len(done_moves),
            1,
            "5 units fit in the oldest layer, so nothing may be split off",
        )
        self.assertAlmostEqual(
            sum(abs(value) for value in done_moves.mapped("value")),
            500.0,
            msg="5 units must be valued on the oldest layer (5 x 100)",
        )

        backorder = self._backorder_of(picking)
        self.assertEqual(len(backorder), 1, "The un-picked 10 must be backordered")
        self.assertAlmostEqual(sum(backorder.move_ids.mapped("product_uom_qty")), 10.0)

        self.assertAlmostEqual(
            self._qty_at_location(), 15.0, msg="20 received - 5 shipped"
        )

    def test_partial_pick_spanning_two_layers(self):
        """20 ordered, 15 picked: the 15 span both layers, so the move is split
        per layer - but still only 15 leave and 5 are backordered."""
        self._two_layers()
        picking = self._make_delivery(20)
        self._pick_and_validate(picking, 15, expect_backorder=True)

        done_moves = self._done_moves(picking)
        self.assertEqual(
            len(done_moves), 2, "One move per consumed FIFO layer (10 + 5)"
        )
        self.assertAlmostEqual(sum(done_moves.mapped("quantity")), 15.0)
        self.assertEqual(
            sorted(done_moves.mapped("quantity")),
            [5.0, 10.0],
            "The split must follow the layers: 10 from the first, 5 from the second",
        )
        self.assertAlmostEqual(
            sum(abs(value) for value in done_moves.mapped("value")),
            10 * 100 + 5 * 150,
            msg="10 units at 100 and 5 at 150",
        )

        backorder = self._backorder_of(picking)
        self.assertEqual(len(backorder), 1)
        self.assertAlmostEqual(sum(backorder.move_ids.mapped("product_uom_qty")), 5.0)

        self.assertAlmostEqual(self._qty_at_location(), 5.0)

    def test_full_pick_still_splits_per_layer(self):
        """Nothing changes when everything ordered is picked: the move is still
        split per layer, valued per layer, and no backorder is created."""
        self._two_layers()
        picking = self._make_delivery(15)
        self._pick_and_validate(picking, 15, expect_backorder=False)

        done_moves = self._done_moves(picking)
        self.assertEqual(len(done_moves), 2)
        self.assertEqual(sorted(done_moves.mapped("quantity")), [5.0, 10.0])
        self.assertAlmostEqual(
            sum(abs(value) for value in done_moves.mapped("value")),
            10 * 100 + 5 * 150,
        )
        self.assertFalse(
            self._backorder_of(picking), "A fully picked transfer has no backorder"
        )
        self.assertAlmostEqual(self._qty_at_location(), 5.0)

    def test_split_leaves_the_ordered_demand_untouched(self):
        """Unit-level check on ``_split_for_fifo_assignment``: with 15 ordered
        and 5 picked it must consume 5 from the stack, split nothing off, and
        leave ``product_uom_qty`` at 15 so core's ``_create_backorder`` can
        still see the 10 that were not shipped."""
        self._two_layers()
        picking = self._make_delivery(15)
        move = picking.move_ids
        move._set_quantity_done(5)
        move.picked = True

        splitted = move._split_for_fifo_assignment()

        self.assertFalse(
            splitted, "5 units come from a single layer - nothing to split off"
        )
        self.assertAlmostEqual(move.quantity, 5.0)
        self.assertAlmostEqual(
            move.product_uom_qty,
            15.0,
            msg="The ordered demand must stay untouched, it is what backorders",
        )
        self.assertAlmostEqual(
            move.value_manual, 500.0, msg="Valued on the oldest layer (5 x 100)"
        )

    def test_consistency_check_blocks_an_inconsistent_split(self):
        """The safety net: if the split ends up accounting for less than what is
        being shipped, the transfer must stop with a clear error instead of
        silently shipping/valuing the wrong quantity. Simulated by making the
        per-slice split under-account by one unit."""
        self._receive(10, 100, "pd_guard_po")
        picking = self._make_delivery(5)
        picking.move_ids._set_quantity_done(5)
        picking.move_ids.picked = True

        def under_accounting_split(_self, move, fifo_list, quantity, vals_list):
            """Drain the stack but leave the move one unit short."""
            fifo_list.clear()
            move.quantity = quantity - 1
            return vals_list, 0

        with self.assertRaises(UserError) as error, self.cr.savepoint():
            with patch.object(
                type(self.env["stock.move"]),
                "_l10n_ro_process_fifo_split",
                under_accounting_split,
            ):
                picking.button_validate()
        self.assertIn("FIFO", error.exception.args[0])

        self.env.invalidate_all()
        self.assertNotEqual(
            picking.state, "done", "Nothing may be shipped when the check fails"
        )
        self.assertAlmostEqual(
            self._qty_at_location(), 10.0, msg="The stock must be left untouched"
        )
