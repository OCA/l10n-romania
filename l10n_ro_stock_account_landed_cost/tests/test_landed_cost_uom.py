# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

"""Landed cost distribution when the receipt is encoded in a secondary UoM.

Core fills ``stock.valuation.adjustment.lines.quantity`` by converting
``move.quantity`` to the product UoM, and the tracked destination quantities
(``l10n.ro.stock.move.tracking``) as well as ``remaining_qty`` are in that
same unit - only ``move.quantity`` itself is in the move's own UoM. Mixing
them makes the per-unit cost and the consumed quantity come out wrong by the
conversion factor (and, when the receipt is in a bigger unit, negative).
"""

import logging

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestLandedCostUom(TestROStockCommon):
    @classmethod
    @TestROStockCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.log_checks = False
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.uom_box10 = cls.env["uom.uom"].create(
            {
                "name": "Box of 10",
                "relative_uom_id": cls.uom_unit.id,
                "relative_factor": 10.0,
            }
        )
        cls.product_box = cls.env["product.product"].create(
            {
                "name": "Product FIFO received by box",
                "is_storable": True,
                "categ_id": cls.category_marfa_fifo.id,
                "invoice_policy": "delivery",
                "purchase_method": "receive",
                "uom_id": cls.uom_unit.id,
                "uom_ids": [(6, 0, [cls.uom_box10.id])],
            }
        )
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.warehouse = cls.location.warehouse_id

    def _make_picking(self, picking_type, src, dest, qty, uom):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": src.id,
                "location_dest_id": dest.id,
            }
        )
        self.env["stock.move"].create(
            {
                "picking_id": picking.id,
                "product_id": self.product_box.id,
                "product_uom": uom.id,
                "product_uom_qty": qty,
                "location_id": src.id,
                "location_dest_id": dest.id,
            }
        )
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move._set_quantity_done(qty)
            move.picked = True
        picking.button_validate()
        return picking

    def _receive(self, qty, uom, unit_price):
        self.product_box.standard_price = unit_price
        return self._make_picking(
            self.warehouse.in_type_id,
            self.supplier_location,
            self.location,
            qty,
            uom,
        )

    def _deliver(self, qty, uom):
        return self._make_picking(
            self.warehouse.out_type_id,
            self.location,
            self.customer_location,
            qty,
            uom,
        )

    def _create_landed_cost(self, picking, amount):
        cost = self.env["stock.landed.cost"].create(
            {
                "picking_ids": [(6, 0, picking.ids)],
                "account_journal_id": self.stock_journal.id,
                "cost_lines": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.landed_cost.id,
                            "name": "Transport",
                            "split_method": "by_quantity",
                            "price_unit": amount,
                        },
                    )
                ],
            }
        )
        cost.compute_landed_cost()
        return cost

    def test_adjustment_line_quantity_in_product_uom(self):
        """The receipt is 2 boxes; the valuation adjustment works on the 20
        units, and the whole cost lands on the still-on-hand receipt."""
        receipt = self._receive(2, self.uom_box10, 10.0)
        in_move = receipt.move_ids
        self.assertEqual(in_move.product_uom, self.uom_box10)
        self.assertAlmostEqual(in_move.quantity, 2.0)
        self.assertAlmostEqual(in_move.product_qty, 20.0)
        self.assertAlmostEqual(in_move.value, 200.0, places=2)

        cost = self._create_landed_cost(receipt, 100.0)
        adj_line = cost.valuation_adjustment_lines
        self.assertEqual(len(adj_line), 1)
        self.assertAlmostEqual(adj_line.quantity, 20.0)
        self.assertAlmostEqual(adj_line.additional_landed_cost, 100.0, places=2)

        cost.button_validate()
        self.assertEqual(cost.state, "done")
        in_move.invalidate_recordset(["value"])
        self.assertAlmostEqual(in_move.value, 300.0, places=2)

    def test_distribution_on_consumed_quantity_in_boxes(self):
        """Half the receipt is already delivered when the cost arrives: the
        consumed share must be 10 of the 20 units, so 50 of the 100."""
        receipt = self._receive(2, self.uom_box10, 10.0)
        in_move = receipt.move_ids
        delivery = self._deliver(1, self.uom_box10)
        out_move = delivery.move_ids
        self.assertAlmostEqual(out_move.product_qty, 10.0)

        in_move.invalidate_recordset(["remaining_qty"])
        self.assertAlmostEqual(in_move.remaining_qty, 10.0)

        cost = self._create_landed_cost(receipt, 100.0)
        adj_line = cost.valuation_adjustment_lines
        self.assertAlmostEqual(adj_line.quantity, 20.0)

        distributed = adj_line.l10n_ro_distributed_valuation_lines
        self.assertTrue(
            distributed, "the consumed part must be distributed on the destination"
        )
        self.assertEqual(distributed.move_id, out_move)
        # 100 over 20 units = 5/unit; 10 units were already consumed.
        self.assertAlmostEqual(sum(distributed.mapped("quantity")), 10.0)
        self.assertAlmostEqual(
            sum(distributed.mapped("additional_landed_cost")), 50.0, places=2
        )

    def test_distribution_receipt_in_smaller_uom(self):
        """Mirror case: the product is kept in boxes and received in units."""
        product = self.env["product.product"].create(
            {
                "name": "Product FIFO kept in boxes",
                "is_storable": True,
                "categ_id": self.category_marfa_fifo.id,
                "purchase_method": "receive",
                "uom_id": self.uom_box10.id,
                "uom_ids": [(6, 0, [self.uom_unit.id])],
            }
        )
        self.product_box = product
        receipt = self._receive(40, self.uom_unit, 30.0)  # 4 boxes at 30 = 120
        in_move = receipt.move_ids
        self.assertAlmostEqual(in_move.quantity, 40.0)
        self.assertAlmostEqual(in_move.product_qty, 4.0)
        self.assertAlmostEqual(in_move.value, 120.0, places=2)

        self._deliver(1, self.uom_box10)
        cost = self._create_landed_cost(receipt, 80.0)
        adj_line = cost.valuation_adjustment_lines
        self.assertAlmostEqual(adj_line.quantity, 4.0)
        distributed = adj_line.l10n_ro_distributed_valuation_lines
        self.assertTrue(distributed)
        # 80 over 4 boxes = 20/box; 1 box consumed.
        self.assertAlmostEqual(sum(distributed.mapped("quantity")), 1.0)
        self.assertAlmostEqual(
            sum(distributed.mapped("additional_landed_cost")), 20.0, places=2
        )
