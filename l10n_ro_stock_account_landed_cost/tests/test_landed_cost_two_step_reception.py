# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

_logger = logging.getLogger(__name__)


class LandedCostTwoStepReceptionCases:
    """Landed cost on a two step reception (Vendors -> Input -> Stock).

    The landed cost is distributed on the reception move and, through the
    move tracking, on the internal move that brings the goods from Input to
    Stock.  The value of the internal move must stay equal to the value of
    the reception it comes from: the landed cost travels along the chain, it
    is not added again at every step.
    """

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _lc_two_steps_warehouse(self):
        warehouse = self.env["stock.warehouse"].search(
            [("lot_stock_id", "=", self.location.id)], limit=1
        )
        warehouse.reception_steps = "two_steps"
        return warehouse

    def _lc_two_steps_purchase(self, product, qty, price):
        purchase = self.env["purchase.order"].create(
            {
                "partner_id": self.supplier_1.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_qty": qty,
                            "price_unit": price,
                        },
                    )
                ],
            }
        )
        purchase.button_confirm()
        return purchase

    def _lc_validate(self, picking, qty):
        picking.move_ids._set_quantity_done(qty)
        picking.move_ids.picked = True
        picking.button_validate()
        if picking.state == "assigned":
            picking._action_done()
        return picking

    def _lc_bill(self, purchase):
        action = purchase.action_create_invoice()
        invoice = self.env["account.move"].browse(action["res_id"])
        invoice.write(
            {
                "date": purchase.date_planned,
                "invoice_date": purchase.date_planned,
                "invoice_date_due": purchase.date_planned,
            }
        )
        invoice.with_context(l10n_ro_approved_price_difference=True).action_post()
        return invoice

    def _lc_landed_cost(self, invoice, pickings, amount):
        return self.create_landed_cost(invoice, pickings, {"landed_cost": amount})

    def _lc_in_move(self, purchase):
        return purchase.picking_ids.move_ids.filtered(
            lambda m: m.picking_id.picking_type_code == "incoming"
        )

    def _lc_stock_value(self, product):
        """Value of what the company holds of ``product``, from the moves."""
        moves = self.env["stock.move"].search(
            [
                ("product_id", "=", product.id),
                ("state", "=", "done"),
                ("company_id", "=", self.env.company.id),
            ]
        )
        return sum(moves.mapped("remaining_value"))

    def _lc_assert(self, move, expected, label):
        self.assertAlmostEqual(
            move.value,
            expected,
            2,
            f"{label} ({move.reference}): expected {expected}, got {move.value}\n"
            f"{move.value_justification}",
        )

    # ------------------------------------------------------------------
    # scenarios
    # ------------------------------------------------------------------
    def test_landed_cost_two_steps_after_storage_fifo(self):
        """Landed cost booked after both steps are done."""
        self._lc_two_steps_warehouse()
        product = self.product_fifo
        purchase = self._lc_two_steps_purchase(product, 10.0, 100.0)
        in_move = self._lc_in_move(purchase)
        self._lc_validate(in_move.picking_id, 10.0)
        int_move = in_move.move_dest_ids
        self.assertTrue(int_move, "the storage move was not generated")
        self._lc_validate(int_move.picking_id, 10.0)
        invoice = self._lc_bill(purchase)
        self._lc_landed_cost(invoice, in_move.picking_id, 200.0)

        self._lc_assert(in_move, 1200.0, "reception move")
        self._lc_assert(int_move, 1200.0, "storage move")
        self.assertAlmostEqual(
            self._lc_stock_value(product),
            1200.0,
            2,
            "the goods must be worth the reception plus the landed cost",
        )

    def test_landed_cost_two_steps_partial_storage(self):
        """Landed cost booked when only a part of the goods reached Stock.

        The share covering the stored quantity follows the storage move, the
        rest stays on what is still in Input.
        """
        self._lc_two_steps_warehouse()
        product = self.product_fifo
        purchase = self._lc_two_steps_purchase(product, 10.0, 100.0)
        in_move = self._lc_in_move(purchase)
        self._lc_validate(in_move.picking_id, 10.0)
        int_move = in_move.move_dest_ids
        self._lc_validate(int_move.picking_id, 6.0)
        int_move = int_move.filtered(lambda m: m.state == "done")
        invoice = self._lc_bill(purchase)
        self._lc_landed_cost(invoice, in_move.picking_id, 200.0)

        self._lc_assert(in_move, 1200.0, "reception move")
        self._lc_assert(int_move, 720.0, "storage move")
        self.assertAlmostEqual(
            self._lc_stock_value(product),
            1200.0,
            2,
            "the goods must be worth the reception plus the landed cost",
        )

    def test_landed_cost_two_steps_before_storage(self):
        """Landed cost booked while the goods are still in Input."""
        self._lc_two_steps_warehouse()
        purchase = self._lc_two_steps_purchase(self.product_fifo, 10.0, 100.0)
        in_move = self._lc_in_move(purchase)
        self._lc_validate(in_move.picking_id, 10.0)
        int_move = in_move.move_dest_ids
        self.assertTrue(int_move, "the storage move was not generated")
        invoice = self._lc_bill(purchase)
        self._lc_landed_cost(invoice, in_move.picking_id, 200.0)
        self._lc_assert(in_move, 1200.0, "reception move")

        self._lc_validate(int_move.picking_id, 10.0)
        self._lc_assert(in_move, 1200.0, "reception move after storage")
        self._lc_assert(int_move, 1200.0, "storage move")
