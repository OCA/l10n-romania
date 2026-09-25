# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from .common import TestROStockCommon


@tagged("post_install", "-at_install")
class TestViewLocation(TestROStockCommon):
    """A move whose location is a `view` gathering several internal locations.

    A warehouse can group several stock locations under a `view` location and
    deliver from it. When the goods are taken from more than one child
    location, the move keeps the `view` as its location (see
    `_set_locations_from_move_line`), while the stock actually leaves internal
    locations - which is what the core valuation looks at, through the move
    lines. The Romanian move type has to be classified the same way, otherwise
    the delivery is left without a move type.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.location_view = cls.env["stock.location"].create(
            {
                "name": "Grouped Stock",
                "usage": "view",
                "location_id": cls.location.location_id.id,
            }
        )
        cls.location_view_1 = cls.env["stock.location"].create(
            {
                "name": "Grouped Stock 1",
                "usage": "internal",
                "location_id": cls.location_view.id,
            }
        )
        cls.location_view_2 = cls.env["stock.location"].create(
            {
                "name": "Grouped Stock 2",
                "usage": "internal",
                "location_id": cls.location_view.id,
            }
        )
        cls.location_customer = cls.env.ref("stock.stock_location_customers")

    def _receive(self, location, qty, price):
        self.product_avg.standard_price = price
        self.env["stock.quant"]._update_available_quantity(
            self.product_avg, location, qty
        )

    def _move(self, location_src, location_dest, qty):
        move = self.env["stock.move"].create(
            {
                "company_id": self.env.company.id,
                "location_id": location_src.id,
                "location_dest_id": location_dest.id,
                "product_id": self.product_avg.id,
                "product_uom": self.product_avg.uom_id.id,
                "product_uom_qty": qty,
            }
        )
        move._action_confirm()
        move._action_assign()
        # the reservation takes the goods from the internal child locations
        self.assertEqual(move.quantity, qty)
        move.picked = True
        move._action_done()
        return move

    def test_delivery_from_view_location(self):
        self._receive(self.location_view_1, 5, 10)
        self._receive(self.location_view_2, 5, 10)

        move = self._move(self.location_view, self.location_customer, 8)

        self.assertEqual(move.state, "done")
        self.assertEqual(
            move.move_line_ids.location_id,
            self.location_view_1 | self.location_view_2,
        )
        self.assertEqual(move.location_id, self.location_view)
        self.assertEqual(move.l10n_ro_move_type, "delivery")

    def test_delivery_from_single_child_of_view_location(self):
        self._receive(self.location_view_1, 5, 10)

        move = self._move(self.location_view, self.location_customer, 3)

        # a single source location replaces the view on the move
        self.assertEqual(move.location_id, self.location_view_1)
        self.assertEqual(move.l10n_ro_move_type, "delivery")

    def test_return_to_view_location(self):
        self._receive(self.location_view_1, 5, 10)
        self._receive(self.location_view_2, 5, 10)
        self._move(self.location_view, self.location_customer, 8)

        move = self.env["stock.move"].create(
            {
                "company_id": self.env.company.id,
                "location_id": self.location_customer.id,
                "location_dest_id": self.location_view.id,
                "product_id": self.product_avg.id,
                "product_uom": self.product_avg.uom_id.id,
                "product_uom_qty": 2,
            }
        )
        move._action_confirm()
        move._action_assign()
        line = move.move_line_ids
        line.write({"location_dest_id": self.location_view_1.id, "quantity": 1})
        line.copy({"location_dest_id": self.location_view_2.id, "quantity": 1})
        move.picked = True
        move._action_done()

        self.assertEqual(move.state, "done")
        self.assertEqual(move.l10n_ro_move_type, "delivery_return")
