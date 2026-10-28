# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

"""Price difference when the receipt move is encoded in a secondary UoM.

With ``stock.propagate_uom`` set, the move generated from a purchase order
keeps the PO line's UoM instead of the product's. ``stock.move.quantity`` is
then expressed in that unit, while the invoiced quantity the price difference
is compared against is converted to the product UoM - so both sides have to
be brought to the product UoM before they are compared.
"""

import logging

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestPriceDifferenceUom(TestROStockCommon):
    @classmethod
    @TestROStockCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.log_checks = False
        cls.env.company.l10n_ro_stock_acc_price_diff = True
        # Without this the procurement normalises the move back to the
        # product UoM (see stock/models/product.py ``_adjust_uom_quantities``)
        # and the bug cannot show up through a purchase order.
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
                "name": "Product FIFO sold by box",
                "is_storable": True,
                "categ_id": cls.category_marfa_fifo.id,
                "invoice_policy": "delivery",
                "purchase_method": "receive",
                "uom_id": cls.uom_unit.id,
                "uom_ids": [(6, 0, [cls.uom_box10.id])],
            }
        )

    def _receive_in_boxes(self, boxes, price_per_box):
        purchase = self.env["purchase.order"].create(
            {
                "partner_id": self.supplier_1.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_box.id,
                            "product_qty": boxes,
                            "product_uom_id": self.uom_box10.id,
                            "price_unit": price_per_box,
                        },
                    )
                ],
            }
        )
        purchase.button_confirm()
        picking = purchase.picking_ids[0]
        picking.move_ids._set_quantity_done(boxes)
        picking.move_ids.picked = True
        picking.button_validate()
        move = purchase.order_line.move_ids.filtered(lambda m: m.state == "done")
        return purchase, move

    def test_price_difference_receipt_in_boxes(self):
        """The bill is 20 per box dearer: the difference is 2 boxes x 20 = 40,
        not the value obtained by comparing 2 (boxes) with 20 (units)."""
        purchase, move = self._receive_in_boxes(boxes=2, price_per_box=100.0)
        # The move really is encoded in boxes - otherwise the test proves
        # nothing.
        self.assertEqual(move.product_uom, self.uom_box10)
        self.assertAlmostEqual(move.quantity, 2.0)
        self.assertAlmostEqual(move.product_qty, 20.0)
        self.assertAlmostEqual(move.value, 200.0, places=2)

        action = purchase.action_create_invoice()
        invoice = self.env["account.move"].browse(action["res_id"])
        invoice.invoice_date = purchase.date_order
        invoice.date = purchase.date_order
        line = invoice.invoice_line_ids[0]
        line.price_unit = 120.0

        diff = line.l10n_ro_get_stock_valuation_difference()
        self.assertEqual(diff["stock_move_id"], move.id)
        self.assertAlmostEqual(diff["qty_diff"], 0.0, places=6)
        self.assertAlmostEqual(diff["value_diff"], 40.0, places=2)

    def test_price_difference_receipt_in_boxes_no_difference(self):
        """Same price on the bill: no difference at all. Comparing a quantity
        in boxes with one in units makes the partial-invoicing branch kick in
        and invent one."""
        purchase, move = self._receive_in_boxes(boxes=3, price_per_box=50.0)
        action = purchase.action_create_invoice()
        invoice = self.env["account.move"].browse(action["res_id"])
        invoice.invoice_date = purchase.date_order
        invoice.date = purchase.date_order
        line = invoice.invoice_line_ids[0]

        diff = line.l10n_ro_get_stock_valuation_difference()
        self.assertAlmostEqual(diff["qty_diff"], 0.0, places=6)
        self.assertAlmostEqual(diff["value_diff"], 0.0, places=2)

    def test_price_difference_partial_invoice_in_boxes(self):
        """Only part of the receipt is invoiced: the pro-rata must be built on
        quantities that are in the same unit."""
        purchase, move = self._receive_in_boxes(boxes=4, price_per_box=100.0)
        action = purchase.action_create_invoice()
        invoice = self.env["account.move"].browse(action["res_id"])
        invoice.invoice_date = purchase.date_order
        invoice.date = purchase.date_order
        line = invoice.invoice_line_ids[0]
        # Invoice 2 of the 4 received boxes, at 130 instead of 100.
        line.quantity = 2.0
        line.price_unit = 130.0

        diff = line.l10n_ro_get_stock_valuation_difference()
        # 2 boxes invoiced out of 4 received -> 20 units invoiced vs 40 in
        # stock: value scaled to the received quantity is 260/20*40 = 520,
        # stock value is 400, so the difference is 120.
        self.assertAlmostEqual(diff["qty_diff"], -20.0, places=6)
        self.assertAlmostEqual(diff["value_diff"], 120.0, places=2)
