# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

_logger = logging.getLogger(__name__)


class TwoStepReceptionHelpers:
    """Building blocks for a two step reception (Vendors -> Input -> Stock).

    Kept apart from the scenarios so that other modules can reuse them; a
    class holding no test method of its own is never collected by the test
    loader.
    """

    def _lc_warehouse(self):
        return self.env["stock.warehouse"].search(
            [("lot_stock_id", "=", self.location.id)], limit=1
        )

    def _lc_two_steps_warehouse(self, steps="two_steps"):
        warehouse = self._lc_warehouse()
        warehouse.reception_steps = steps
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

    def _lc_account_balance(self, account):
        """Balance of ``account``, from the posted entries."""
        return sum(
            self.env["account.move.line"]
            .search(
                [
                    ("account_id", "=", account.id),
                    ("parent_state", "=", "posted"),
                    ("company_id", "=", self.env.company.id),
                ]
            )
            .mapped("balance")
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

    def _lc_move_picking(self, picking_type, product, qty, source, destination):
        """Create, reserve and validate a single move picking."""
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": source.id,
                "location_dest_id": destination.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "location_id": source.id,
                            "location_dest_id": destination.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        self._lc_validate(picking, qty)
        return picking.move_ids.filtered(lambda m: m.state == "done")

    def _lc_internal_transfer(self, product, qty, destination, source=None):
        """Move ``qty`` of ``product`` to another internal location."""
        return self._lc_move_picking(
            self._lc_warehouse().int_type_id,
            product,
            qty,
            source or self.location,
            destination,
        )

    def _lc_transit_transfer(self, product, qty, source=None):
        """Move ``qty`` to the second warehouse, through the transit location.

        Two legs: out of the warehouse into transit, then a pushed move from
        transit into the other warehouse, which holds its own valuation
        account - the cost has to reach it too.
        """
        move_out = self.env["stock.move"].create(
            {
                "company_id": self.env.company.id,
                "location_id": (source or self.location).id,
                "location_dest_id": self.transit_loc.id,
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": qty,
                "route_ids": [(4, self.transit_route.id)],
            }
        )
        move_out._action_confirm()
        move_out._action_assign()
        move_out._set_quantity_done(qty)
        move_out.picked = True
        move_out._action_done()
        move_in = move_out.move_dest_ids
        self.assertTrue(move_in, "the transit push rule created no second leg")
        move_in.picked = True
        move_in.picking_id.button_validate()
        return (
            move_out.filtered(lambda m: m.state == "done"),
            move_in.filtered(lambda m: m.state == "done"),
        )

    def _lc_deliver(self, product, qty, source=None, warehouse=None):
        """Ship ``qty`` of ``product`` out of a warehouse."""
        picking_type = (warehouse or self._lc_warehouse()).out_type_id
        return self._lc_move_picking(
            picking_type,
            product,
            qty,
            source or self.location,
            picking_type.default_location_dest_id,
        )

    def _lc_chain(self, first_move, qty):
        """Validate every step after the reception, returning the moves."""
        chain = []
        move = first_move.move_dest_ids
        while move:
            self.assertTrue(move, "a step of the reception chain is missing")
            self._lc_validate(move.picking_id, qty)
            move = move.filtered(lambda m: m.state == "done")
            chain.append(move)
            move = move.move_dest_ids
        return chain


class LandedCostTwoStepReceptionCases(TwoStepReceptionHelpers):
    """Landed cost on a two step reception.

    The landed cost is distributed on the reception move and, through the
    move tracking, on the internal move that brings the goods from Input to
    Stock.  The value of the internal move must stay equal to the value of
    the reception it comes from: the landed cost travels along the chain, it
    is not added again at every step.
    """

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

    def test_landed_cost_three_steps_after_storage(self):
        """Landed cost on a three step reception (Input -> Quality -> Stock).

        The goods pass through two moves after the reception, one feeding the
        other, and the landed cost has to reach the end of the chain: each
        step carries the whole quantity, so each is worth the reception plus
        the whole landed cost, not a share of it.
        """
        self._lc_two_steps_warehouse(steps="three_steps")
        product = self.product_fifo
        purchase = self._lc_two_steps_purchase(product, 10.0, 100.0)
        in_move = self._lc_in_move(purchase)
        self._lc_validate(in_move.picking_id, 10.0)
        quality_move, storage_move = self._lc_chain(in_move, 10.0)
        invoice = self._lc_bill(purchase)
        self._lc_landed_cost(invoice, in_move.picking_id, 200.0)

        self._lc_assert(in_move, 1200.0, "reception move")
        self._lc_assert(quality_move, 1200.0, "quality control move")
        self._lc_assert(storage_move, 1200.0, "storage move")
        self.assertAlmostEqual(
            self._lc_stock_value(product),
            1200.0,
            2,
            "the goods must be worth the reception plus the landed cost",
        )

    def _landed_cost_delivered_before_cost(self, steps, expected_chain):
        """Goods shipped out before the landed cost is booked.

        The delivery was valued at the cost of the goods as it stood then,
        so the share of the landed cost covering what was shipped has to
        reach it; the rest stays with what is still on hand.
        """
        self._lc_two_steps_warehouse(steps=steps)
        product = self.product_fifo
        purchase = self._lc_two_steps_purchase(product, 10.0, 100.0)
        in_move = self._lc_in_move(purchase)
        self._lc_validate(in_move.picking_id, 10.0)
        chain = self._lc_chain(in_move, 10.0)
        out_move = self._lc_deliver(product, 4.0)
        self._lc_assert(out_move, 400.0, "delivery before the landed cost")

        invoice = self._lc_bill(purchase)
        self._lc_landed_cost(invoice, in_move.picking_id, 200.0)

        self._lc_assert(in_move, 1200.0, "reception move")
        for move, label in zip(chain, expected_chain, strict=True):
            self._lc_assert(move, 1200.0, label)
        self._lc_assert(out_move, 480.0, "delivery after the landed cost")
        self.assertAlmostEqual(
            self._lc_stock_value(product),
            720.0,
            2,
            "what is left on hand carries the rest of the landed cost",
        )

    def test_landed_cost_two_steps_delivered_before_cost(self):
        self._landed_cost_delivered_before_cost("two_steps", ["storage move"])

    def test_landed_cost_three_steps_delivered_before_cost(self):
        self._landed_cost_delivered_before_cost(
            "three_steps", ["quality control move", "storage move"]
        )

    def _landed_cost_transferred_then_delivered(self, steps, chain_labels):
        """A longer chain: reception steps, an internal move, then a delivery.

        The internal move both receives and gives away the goods, so it is
        the step most likely to break a chain: it has to carry the cost of
        everything it holds and still pass on only the share that leaves it.
        """
        self._lc_two_steps_warehouse(steps=steps)
        product = self.product_fifo
        purchase = self._lc_two_steps_purchase(product, 10.0, 100.0)
        in_move = self._lc_in_move(purchase)
        self._lc_validate(in_move.picking_id, 10.0)
        chain = self._lc_chain(in_move, 10.0)
        transfer_move = self._lc_internal_transfer(product, 10.0, self.location_sub_1)
        self._lc_assert(transfer_move, 1000.0, "transfer before the landed cost")
        out_move = self._lc_deliver(product, 4.0, source=self.location_sub_1)
        self._lc_assert(out_move, 400.0, "delivery before the landed cost")

        invoice = self._lc_bill(purchase)
        self._lc_landed_cost(invoice, in_move.picking_id, 200.0)

        self._lc_assert(in_move, 1200.0, "reception move")
        for move, label in zip(chain, chain_labels, strict=True):
            self._lc_assert(move, 1200.0, label)
        self._lc_assert(transfer_move, 1200.0, "internal transfer")
        self._lc_assert(out_move, 480.0, "delivery")
        self.assertAlmostEqual(
            self._lc_stock_value(product),
            720.0,
            2,
            "what is left on hand carries the rest of the landed cost",
        )

    def test_landed_cost_two_steps_transferred_then_delivered(self):
        self._landed_cost_transferred_then_delivered("two_steps", ["storage move"])

    def test_landed_cost_three_steps_transferred_then_delivered(self):
        self._landed_cost_transferred_then_delivered(
            "three_steps", ["quality control move", "storage move"]
        )

    def test_landed_cost_transit_transfer_then_delivered(self):
        """Reception in two steps, a transit transfer in two legs, a delivery.

        The goods end up in the other warehouse, which keeps its own
        valuation account, so the cost has to follow them across both legs
        of the transit and still split correctly on what is shipped out.
        """
        self._lc_two_steps_warehouse()
        product = self.product_fifo
        purchase = self._lc_two_steps_purchase(product, 10.0, 100.0)
        in_move = self._lc_in_move(purchase)
        self._lc_validate(in_move.picking_id, 10.0)
        (storage_move,) = self._lc_chain(in_move, 10.0)
        transit_out, transit_in = self._lc_transit_transfer(product, 10.0)
        self._lc_assert(transit_out, 1000.0, "transit leg out before the cost")
        self._lc_assert(transit_in, 1000.0, "transit leg in before the cost")
        warehouse2 = self.env["stock.warehouse"].search(
            [("lot_stock_id", "=", self.location1.id)], limit=1
        )
        out_move = self._lc_deliver(
            product, 4.0, source=self.location1, warehouse=warehouse2
        )
        self._lc_assert(out_move, 400.0, "delivery before the landed cost")

        invoice = self._lc_bill(purchase)
        self._lc_landed_cost(invoice, in_move.picking_id, 200.0)

        self._lc_assert(in_move, 1200.0, "reception move")
        self._lc_assert(storage_move, 1200.0, "storage move")
        self._lc_assert(transit_out, 1200.0, "transit leg out")
        self._lc_assert(transit_in, 1200.0, "transit leg in")
        self._lc_assert(out_move, 480.0, "delivery")
        self.assertAlmostEqual(
            self._lc_stock_value(product),
            720.0,
            2,
            "what is left in the other warehouse carries the rest",
        )
        self.assertAlmostEqual(
            self._lc_account_balance(
                self.location1.l10n_ro_property_stock_valuation_account_id
            ),
            720.0,
            2,
            "the other warehouse must account for what it holds",
        )
        self.assertAlmostEqual(
            self._lc_account_balance(self.account_valuation),
            0.0,
            2,
            "nothing may be left behind in the first warehouse or in transit",
        )
