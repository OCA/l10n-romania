# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


class FifoMultiOriginCases:
    """A receipt fed by several origin moves takes its value from all of them.

    In a two-step transfer the outgoing leg is split by FIFO into one move per
    stock layer, and every piece keeps the link to the receipt at the
    destination. The receipt used to read only the first origin, and to read
    ``move_orig_ids.reference`` as if there were one: ``Expected singleton``.
    """

    def _chained_move(self, src, dest, qty, **extra):
        return self.env["stock.move"].create(
            {
                "product_id": self.product_fifo.id,
                "product_uom_qty": qty,
                "location_id": src.id,
                "location_dest_id": dest.id,
                **extra,
            }
        )

    def _done(self, move):
        move._action_assign()
        move.quantity = move.product_uom_qty
        move.picked = True
        move._action_done()

    def test_fifo_receipt_valued_from_every_origin(self):
        self._receive(10, 100, 1)
        self._receive(10, 120, 2)
        dest = self._chained_move(self.transit_loc, self.location1, 15)
        origin = self._chained_move(
            self.location,
            self.transit_loc,
            15,
            picking_type_id=self.transit_transfer.id,
            move_dest_ids=[(4, dest.id)],
        )
        (origin | dest)._action_confirm()
        self._done(origin)
        origins = dest.move_orig_ids
        self.assertEqual(len(origins), 2, "the FIFO split feeds the receipt twice")
        # on Odoo 20 the value of an outgoing move is negative
        self.assertAlmostEqual(abs(sum(origins.mapped("value"))), 10 * 100 + 5 * 120)
        self._done(dest)
        self.assertEqual(dest.state, "done")
        self.assertAlmostEqual(dest.value, 10 * 100 + 5 * 120)
