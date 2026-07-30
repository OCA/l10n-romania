# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from .common import TestROStockCommon


@tagged("post_install", "-at_install")
class TestROStockFifoZeroQty(TestROStockCommon):
    """An incoming move with nothing left to consume (its valued quantity is
    zero) must not be split off from the outgoing move: ``_split`` returns no
    values for a zero quantity, which used to raise ``IndexError: list index
    out of range`` in ``_l10n_ro_process_fifo_split``.

    ``_run_fifo_layers`` returns slices of the incoming moves making up the
    location stack - 19.0 has no ``stock.valuation.layer`` any more."""

    def _receive(self, qty, price, index):
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

    def _deliver(self, qty, index):
        sale = self.create_sale_order(
            {
                "currency_id": self.ron,
                "partner_id": self.customer_1,
                "product_id": self.product_fifo,
                "qty": qty,
                "stock_qty": qty,
                "inv_qty": qty,
                "price": 150,
                "inv_price": 150,
                "advance": 0,
                "discount": 0,
                "index": index,
            }
        )
        return sale.picking_ids.move_ids.filtered(
            lambda m: m.product_id == self.product_fifo and m.state == "done"
        )

    def _zero_out_reception(self, move):
        """Correct a validated reception down to zero: the move stays done and
        incoming, but it values nothing (``_get_valued_qty()`` is 0). Its stock
        is given back, so it no longer backs any quant."""
        line = move.move_line_ids[:1]
        line.write({"quantity": 0})
        move.invalidate_recordset(["quantity", "value"])
        self.assertEqual(move.state, "done")
        self.assertTrue(move.is_in)
        self.assertAlmostEqual(move._get_valued_qty(), 0.0)
        return move

    def test_fifo_process_split_skips_zero_quantity_slice(self):
        """``_l10n_ro_process_fifo_split`` must drop a zero-quantity slice and
        keep consuming the next one, instead of raising IndexError."""
        in_move = self._receive(10, 100, "zl_po")
        out_move = self.env["stock.move"].create(
            {
                "product_id": self.product_fifo.id,
                "product_uom_qty": 5,
                "product_uom": self.product_fifo.uom_id.id,
                "location_id": self.location.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "company_id": self.env.company.id,
            }
        )
        out_move._action_confirm()
        out_move._action_assign()
        fifo_list = [
            {
                "move_id": False,
                "quantity": 0.0,
                "value": 0.0,
                "description": "Nothing left to consume",
            },
            {
                "move_id": in_move.id,
                "quantity": 5.0,
                "value": 500.0,
                "description": in_move.display_name,
            },
        ]
        # First slice: zero quantity -> skipped, nothing split off.
        split_vals, quantity = self.env["stock.move"]._l10n_ro_process_fifo_split(
            out_move, fifo_list, 5.0, []
        )
        self.assertEqual(
            split_vals, [], "A zero-quantity slice must not generate a split move"
        )
        self.assertAlmostEqual(
            quantity, 5.0, msg="The quantity left to assign must stay untouched"
        )
        self.assertEqual(len(fifo_list), 1, "The zero slice must be consumed")
        self.assertAlmostEqual(out_move.product_uom_qty, 5.0)

        # Second slice: covers the whole move -> valued, no split.
        split_vals, quantity = self.env["stock.move"]._l10n_ro_process_fifo_split(
            out_move, fifo_list, quantity, split_vals
        )
        self.assertEqual(split_vals, [])
        self.assertAlmostEqual(quantity, 0.0)
        self.assertAlmostEqual(out_move.value_manual, 500.0)

    def test_fifo_out_move_with_zero_valued_reception_in_stack(self):
        """An incoming move that values nothing must not show up in the FIFO
        stack, and a delivery exceeding the stock must still validate."""
        # Two receptions of 10 @ 100; the newer one is corrected down to 0.
        self._receive(10, 100, "zl_po1")
        self._zero_out_reception(self._receive(10, 100, "zl_po2"))
        product_at_loc = self.product_fifo.with_context(
            location=self.location.id, strict=True
        )
        self.assertAlmostEqual(
            product_at_loc.qty_available,
            10.0,
            msg="Only the first reception is left in stock",
        )

        # No zero-quantity slice may reach the outgoing split.
        slices = self.product_fifo.with_context(
            location=self.location.ids
        )._run_fifo_layers(15, location=self.location)
        self.assertTrue(slices)
        for fifo_slice in slices:
            self.assertGreater(
                fifo_slice["quantity"],
                0,
                f"No FIFO slice may have a zero quantity: {slices}",
            )

        # Delivering 15 with 10 on hand: 10 from the reception + 5 on negative
        # stock, valued at the standard price.
        out_moves = self._deliver(15, "zl_so")
        self.assertTrue(out_moves, "The delivery must be validated")
        self.assertAlmostEqual(sum(out_moves.mapped("quantity")), 15.0)
        self.assertAlmostEqual(
            sum(abs(value) for value in out_moves.mapped("value")),
            10 * 100 + 5 * self.product_fifo.standard_price,
        )
