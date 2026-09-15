# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

"""FIFO per location with a move UoM different from the product UoM.

The RO FIFO stack, ``_run_fifo_layers`` and ``stock.move._split`` all work in
the product's *reference* UoM, while ``stock.move.quantity`` is stored in the
move's *own* UoM. Every test here ships or receives in a secondary unit -
smaller (cm, mm), bigger (roll = 50 m) and mixed - so any place that treats
the two as interchangeable shows up as a wrong value, a wrong split quantity
or the FIFO consistency ``UserError``.
"""

import logging

from odoo.tests import tagged

from .common import TestROStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockFifoUom(TestROStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.fifo_per_location = True
        # Reference unit of its own UoM tree (19.0 dropped uom.category in
        # favour of the ``relative_uom_id`` parent tree).
        cls.uom_m = cls.env["uom.uom"].create(
            {
                "name": "Test Meter",
                "relative_factor": 1.0,
            }
        )
        # Smaller than the reference: 100 cm = 1 m.
        cls.uom_cm = cls.env["uom.uom"].create(
            {
                "name": "Test Centimeter",
                "relative_uom_id": cls.uom_m.id,
                "relative_factor": 0.01,
            }
        )
        # Much smaller than the reference: 1000 mm = 1 m.
        cls.uom_mm = cls.env["uom.uom"].create(
            {
                "name": "Test Millimeter",
                "relative_uom_id": cls.uom_m.id,
                "relative_factor": 0.001,
            }
        )
        # Bigger than the reference: 1 roll = 50 m.
        cls.uom_roll = cls.env["uom.uom"].create(
            {
                "name": "Test Roll",
                "relative_uom_id": cls.uom_m.id,
                "relative_factor": 50.0,
            }
        )
        cls.product_uom_fifo = cls.env["product.product"].create(
            {
                "name": "Product FIFO in meters",
                "is_storable": True,
                "categ_id": cls.category_marfa_fifo.id,
                "invoice_policy": "delivery",
                "purchase_method": "receive",
                "uom_id": cls.uom_m.id,
            }
        )
        cls.warehouse = cls.location.warehouse_id
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.customer_location = cls.env.ref("stock.stock_location_customers")

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _set_product_unit_precision(self, digits):
        """Raise/lower the global 'Product Unit' precision, which is what
        every UoM uses as rounding in 19.0."""
        precision = self.env.ref("uom.decimal_product_uom")
        precision.digits = digits
        self.env.registry.clear_cache()
        self.env["uom.uom"].invalidate_model(["rounding"])

    def _make_picking(self, picking_type, location, location_dest, qty, uom, product):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": location.id,
                "location_dest_id": location_dest.id,
            }
        )
        self.env["stock.move"].create(
            {
                "picking_id": picking.id,
                "product_id": product.id,
                "product_uom": uom.id,
                "product_uom_qty": qty,
                "location_id": location.id,
                "location_dest_id": location_dest.id,
            }
        )
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move._set_quantity_done(qty)
            move.picked = True
        picking.button_validate()
        return picking

    def _receive(self, qty, uom, unit_price, product=None):
        """Receive ``qty`` ``uom`` valued at ``unit_price`` per *product* UoM.

        Plain receipts (no PO/bill) fall back to ``standard_price``, which is
        always expressed per product UoM - the layer cost is therefore
        ``unit_price * qty_in_product_uom``."""
        product = product or self.product_uom_fifo
        product.standard_price = unit_price
        return self._make_picking(
            self.warehouse.in_type_id,
            self.supplier_location,
            self.location,
            qty,
            uom,
            product,
        )

    def _deliver(self, qty, uom, product=None):
        product = product or self.product_uom_fifo
        return self._make_picking(
            self.warehouse.out_type_id,
            self.location,
            self.customer_location,
            qty,
            uom,
            product,
        )

    def _out_moves(self, picking):
        return picking.move_ids.sorted("id")

    # ------------------------------------------------------------------
    # smaller UoM on the outgoing move
    # ------------------------------------------------------------------
    def test_out_smaller_uom_single_layer(self):
        """One layer, delivery encoded in cm: no split, value from the layer."""
        self._receive(10, self.uom_m, 20)
        out = self._deliver(250, self.uom_cm)
        moves = self._out_moves(out)
        self.assertEqual(len(moves), 1, "A single FIFO layer must not split")
        move = moves[0]
        self.assertEqual(move.product_uom, self.uom_cm)
        self.assertAlmostEqual(move.quantity, 250.0)
        self.assertAlmostEqual(move.product_qty, 2.5)
        # 2.5 m at 20/m
        self.assertAlmostEqual(abs(move.value), 50.0, places=2)

    def test_out_smaller_uom_multi_layer_split(self):
        """Two layers, delivery in cm: the split must be made in the product
        UoM but stored back in the move UoM."""
        self._receive(4, self.uom_m, 10)
        self._receive(6, self.uom_m, 20)
        out = self._deliver(500, self.uom_cm)
        moves = self._out_moves(out)
        self.assertEqual(len(moves), 2, "5 m over a 4 m + 6 m stack must split")
        qty_by_value = sorted(
            (round(m.product_qty, 6), round(abs(m.value), 2)) for m in moves
        )
        # 4 m at 10 = 40, then 1 m at 20 = 20
        self.assertEqual(qty_by_value, [(1.0, 20.0), (4.0, 40.0)])
        for move in moves:
            self.assertEqual(move.product_uom, self.uom_cm)
            self.assertAlmostEqual(move.quantity, move.product_qty * 100.0, places=2)
        self.assertAlmostEqual(sum(abs(m.value) for m in moves), 60.0, places=2)
        self.assertAlmostEqual(sum(m.product_qty for m in moves), 5.0)

    def test_out_smaller_uom_consumes_whole_stack(self):
        """The delivery empties the stack exactly - the last slice is the
        no-split branch, which must value ``move.quantity`` converted."""
        self._receive(2, self.uom_m, 15)
        self._receive(3, self.uom_m, 25)
        out = self._deliver(500, self.uom_cm)
        moves = self._out_moves(out)
        self.assertEqual(len(moves), 2)
        self.assertAlmostEqual(sum(m.product_qty for m in moves), 5.0)
        # 2 m at 15 + 3 m at 25 = 105
        self.assertAlmostEqual(sum(abs(m.value) for m in moves), 105.0, places=2)
        self.assertAlmostEqual(
            self.product_uom_fifo.with_context(location=self.location.id).qty_available,
            0.0,
        )

    # ------------------------------------------------------------------
    # bigger UoM
    # ------------------------------------------------------------------
    def test_out_bigger_uom(self):
        """Delivery encoded in rolls (1 roll = 50 m) over a stack in m."""
        self._receive(200, self.uom_m, 5)
        out = self._deliver(2, self.uom_roll)
        moves = self._out_moves(out)
        self.assertEqual(len(moves), 1)
        move = moves[0]
        self.assertAlmostEqual(move.quantity, 2.0)
        self.assertAlmostEqual(move.product_qty, 100.0)
        self.assertAlmostEqual(abs(move.value), 500.0, places=2)

    def test_in_bigger_uom_stack_remaining(self):
        """Reception encoded in rolls: the stack quantity for that move must
        be read in the product UoM, not in rolls."""
        receipt = self._receive(2, self.uom_roll, 5)
        in_move = receipt.move_ids
        self.assertAlmostEqual(in_move.quantity, 2.0)
        self.assertAlmostEqual(in_move.product_qty, 100.0)
        self.assertAlmostEqual(in_move.value, 500.0, places=2)
        in_move.invalidate_recordset(["remaining_qty", "remaining_value"])
        self.assertAlmostEqual(in_move.remaining_qty, 100.0)
        self.assertAlmostEqual(in_move.remaining_value, 500.0, places=2)

        out = self._deliver(30, self.uom_m)
        self.assertAlmostEqual(abs(out.move_ids.value), 150.0, places=2)
        in_move.invalidate_recordset(["remaining_qty", "remaining_value"])
        self.assertAlmostEqual(in_move.remaining_qty, 70.0)
        self.assertAlmostEqual(in_move.remaining_value, 350.0, places=2)

    def test_in_bigger_uom_out_smaller_uom_mixed_layers(self):
        """Stack built in rolls and in cm, consumed in m across both layers."""
        self._receive(3, self.uom_roll, 2)  # 150 m at 2 = 300
        self._receive(5000, self.uom_cm, 6)  # 50 m at 6 = 300
        out = self._deliver(180, self.uom_m)
        moves = self._out_moves(out)
        self.assertEqual(len(moves), 2)
        self.assertAlmostEqual(sum(m.product_qty for m in moves), 180.0)
        # 150 m at 2 = 300, then 30 m at 6 = 180
        self.assertAlmostEqual(sum(abs(m.value) for m in moves), 480.0, places=2)
        values = sorted(round(abs(m.value), 2) for m in moves)
        self.assertEqual(values, [180.0, 300.0])

    # ------------------------------------------------------------------
    # rounding
    # ------------------------------------------------------------------
    def test_out_mm_requires_precision(self):
        """mm over a product in m only works with enough 'Product Unit'
        precision; with it, a non-round quantity must still balance."""
        self._set_product_unit_precision(6)
        self._receive(1, self.uom_m, 300)
        out = self._deliver(333, self.uom_mm)
        move = self._out_moves(out)[0]
        self.assertAlmostEqual(move.product_qty, 0.333, places=6)
        self.assertAlmostEqual(abs(move.value), 99.9, places=2)

    def test_out_mm_rounding_residue_across_layers(self):
        """Layers that do not divide evenly: the split must consume exactly
        the shipped quantity, residue included."""
        self._set_product_unit_precision(6)
        self._receive(333, self.uom_mm, 300)  # 0.333 m at 300 = 99.9
        self._receive(667, self.uom_mm, 600)  # 0.667 m at 600 = 400.2
        out = self._deliver(1000, self.uom_mm)  # 1 m
        moves = self._out_moves(out)
        self.assertAlmostEqual(sum(m.product_qty for m in moves), 1.0, places=6)
        self.assertAlmostEqual(sum(abs(m.value) for m in moves), 500.1, places=2)
        self.assertAlmostEqual(
            self.product_uom_fifo.with_context(location=self.location.id).qty_available,
            0.0,
            places=6,
        )

    def test_out_thirds_of_a_layer(self):
        """A quantity that is not representable exactly in the move UoM must
        not trip the FIFO consistency check."""
        self._set_product_unit_precision(6)
        self._receive(10, self.uom_m, 3)
        for _i in range(3):
            self._deliver(3333, self.uom_mm)
        remaining = self.product_uom_fifo.with_context(
            location=self.location.id
        ).qty_available
        self.assertAlmostEqual(remaining, 10 - 3 * 3.333, places=6)

    # ------------------------------------------------------------------
    # negative stock compensation
    # ------------------------------------------------------------------
    def test_negative_stock_pending_qty_in_product_uom(self):
        """A delivery on an empty stack stores its pending quantity in the
        product UoM, which is what the compensation on the next IN consumes."""
        self.env.company.fifo_location_negative_compensation = True
        self.product_uom_fifo.standard_price = 20
        out = self._deliver(250, self.uom_cm)
        move = self._out_moves(out)[0]
        self.assertAlmostEqual(move.fifo_neg_pending_qty, 2.5)
        self.assertAlmostEqual(move.fifo_neg_origin_value, 50.0, places=2)
        self.assertAlmostEqual(abs(move.value), 50.0, places=2)

        # Next reception at 30/m compensates the 2.5 m at 20/m.
        self._receive(10, self.uom_m, 30)
        self.assertAlmostEqual(move.fifo_neg_pending_qty, 0.0)
        self.assertAlmostEqual(abs(move.value), 75.0, places=2)
