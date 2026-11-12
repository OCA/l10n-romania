# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

"""Valued picking report when the operation line is in a secondary UoM.

Every unit price the report builds is per product UoM: the one converted
from the sale line with ``_compute_price``, and ``value / _get_valued_qty()``
taken from ``_get_value_data``. ``stock.move.line.quantity`` is stored in the
line's own UoM, so it has to be converted before it multiplies any of them.
"""

import logging

from odoo.tests import tagged

from .common import TestStockPickingValued

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockPickingValuedUom(TestStockPickingValued):
    @classmethod
    @TestStockPickingValued.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        # Without this the procurement normalises the delivery move back to
        # the product UoM (stock/models/product.py ``_adjust_uom_quantities``)
        # and the sale-line scenario below would never reach the report with
        # a line in boxes.
        cls.env["ir.config_parameter"].sudo().set_param("stock.propagate_uom", "1")
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
                "name": "Product FIFO shipped by box",
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

    def _make_picking(self, picking_type, src, dest, qty, uom, validate=True):
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
        if validate:
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

    def test_valued_from_stock_move_in_boxes(self):
        """Delivery of 1 box out of a stack at 10/unit: 100, not 10."""
        self._receive(3, self.uom_box10, 10.0)
        delivery = self._make_picking(
            self.warehouse.out_type_id,
            self.location,
            self.customer_location,
            1,
            self.uom_box10,
        )
        line = delivery.move_line_ids
        self.assertEqual(len(line), 1)
        self.assertEqual(line.product_uom_id, self.uom_box10)
        self.assertAlmostEqual(line.quantity, 1.0)
        self.assertAlmostEqual(line.quantity_product_uom, 10.0)
        # The unit price stays per product UoM ...
        self.assertAlmostEqual(line.l10n_ro_price_unit, 10.0, places=2)
        # ... so the subtotal must cover the 10 units actually shipped.
        self.assertAlmostEqual(line.l10n_ro_price_subtotal, 100.0, places=2)
        self.assertAlmostEqual(line.l10n_ro_price_total, 100.0, places=2)

    def test_valued_from_sale_line_in_boxes(self):
        """Sale line priced per box: the report must show the price per unit
        and a subtotal covering the whole box."""
        self._receive(3, self.uom_box10, 10.0)
        order = self.env["sale.order"].create(
            {
                "partner_id": self.customer_1.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_box.id,
                            "product_uom_qty": 1,
                            "product_uom_id": self.uom_box10.id,
                            "price_unit": 200.0,
                        },
                    )
                ],
            }
        )
        order.action_confirm()
        picking = order.picking_ids
        picking.action_assign()
        for move in picking.move_ids:
            move.picked = True
        picking.button_validate()

        line = picking.move_line_ids
        self.assertEqual(len(line), 1)
        self.assertEqual(line.product_uom_id, self.uom_box10)
        self.assertAlmostEqual(line.quantity, 1.0)
        self.assertAlmostEqual(line.quantity_product_uom, 10.0)
        # 200 per box -> 20 per unit, over 10 units -> 200.
        self.assertAlmostEqual(line.l10n_ro_price_unit, 20.0, places=2)
        self.assertAlmostEqual(line.l10n_ro_price_subtotal, 200.0, places=2)

    def test_valued_from_stock_move_in_smaller_uom(self):
        """Mirror case: product kept in boxes, delivery encoded in units."""
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
        self._receive(4, self.uom_box10, 30.0)  # 4 boxes at 30/box
        delivery = self._make_picking(
            self.warehouse.out_type_id,
            self.location,
            self.customer_location,
            20,
            self.uom_unit,
        )
        line = delivery.move_line_ids
        self.assertAlmostEqual(line.quantity, 20.0)
        self.assertAlmostEqual(line.quantity_product_uom, 2.0)
        self.assertAlmostEqual(line.l10n_ro_price_unit, 30.0, places=2)
        self.assertAlmostEqual(line.l10n_ro_price_subtotal, 60.0, places=2)
