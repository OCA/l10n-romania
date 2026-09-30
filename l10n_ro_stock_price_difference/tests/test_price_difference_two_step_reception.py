# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon
from odoo.addons.l10n_ro_stock_account_landed_cost.tests import (
    test_landed_cost_two_step_reception as lc_two_steps,
)

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestPriceDifferenceTwoStepReception(
    lc_two_steps.TwoStepReceptionHelpers, TestROStockCommon
):
    """A bill priced above the reception, on a two step reception.

    The difference is capitalised through a landed cost of its own, which is
    not distributed on the move it is computed from - the value there already
    comes from the bill - but only on the moves that consumed it.  The storage
    move must therefore end up carrying the bill price exactly once, the same
    way a plain landed cost does.
    """

    @classmethod
    @TestROStockCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.l10n_ro_cost_type = "price_diff"
        cls.l10n_ro_approved_price_difference = True
        cls.env.company.l10n_ro_stock_acc_price_diff = True

    def _bill_at(self, purchase, price):
        action = purchase.action_create_invoice()
        invoice = self.env["account.move"].browse(action["res_id"])
        invoice.invoice_line_ids.write({"price_unit": price})
        invoice.write(
            {
                "date": purchase.date_planned,
                "invoice_date": purchase.date_planned,
                "invoice_date_due": purchase.date_planned,
            }
        )
        invoice.with_context(l10n_ro_approved_price_difference=True).action_post()
        return invoice

    def test_price_difference_two_steps_after_storage(self):
        self._lc_two_steps_warehouse()
        product = self.product_fifo
        purchase = self._lc_two_steps_purchase(product, 10.0, 100.0)
        in_move = self._lc_in_move(purchase)
        self._lc_validate(in_move.picking_id, 10.0)
        int_move = in_move.move_dest_ids
        self.assertTrue(int_move, "the storage move was not generated")
        self._lc_validate(int_move.picking_id, 10.0)

        self._bill_at(purchase, 120.0)

        self._lc_assert(in_move, 1200.0, "reception move")
        self._lc_assert(int_move, 1200.0, "storage move")
        self.assertAlmostEqual(
            self._lc_stock_value(product),
            1200.0,
            2,
            "the goods must be worth the billed price",
        )

    def test_price_difference_two_steps_partial_storage(self):
        """Only a part of the goods reached Stock when the bill arrives.

        Splitting the storage move off the FIFO stack pins its value, which
        spares it the whole question of what it inherits from the reception;
        the scenario is kept because nothing else covered a partly stored
        two step reception being billed at another price.
        """
        self._lc_two_steps_warehouse()
        product = self.product_fifo
        purchase = self._lc_two_steps_purchase(product, 10.0, 100.0)
        in_move = self._lc_in_move(purchase)
        self._lc_validate(in_move.picking_id, 10.0)
        int_move = in_move.move_dest_ids
        self._lc_validate(int_move.picking_id, 6.0)
        int_move = int_move.filtered(lambda m: m.state == "done")

        self._bill_at(purchase, 120.0)

        self._lc_assert(in_move, 1200.0, "reception move")
        self._lc_assert(int_move, 720.0, "storage move")
        self.assertAlmostEqual(
            self._lc_stock_value(product),
            1200.0,
            2,
            "the goods must be worth the billed price",
        )

    def test_price_difference_three_steps(self):
        """Three step reception: the difference has to reach the last step."""
        self._lc_two_steps_warehouse(steps="three_steps")
        product = self.product_fifo
        purchase = self._lc_two_steps_purchase(product, 10.0, 100.0)
        in_move = self._lc_in_move(purchase)
        self._lc_validate(in_move.picking_id, 10.0)
        quality_move, storage_move = self._lc_chain(in_move, 10.0)

        self._bill_at(purchase, 120.0)

        self._lc_assert(in_move, 1200.0, "reception move")
        self._lc_assert(quality_move, 1200.0, "quality control move")
        self._lc_assert(storage_move, 1200.0, "storage move")
        self.assertAlmostEqual(
            self._lc_stock_value(product),
            1200.0,
            2,
            "the goods must be worth the billed price",
        )

    def _price_difference_delivered_before_bill(self, steps):
        """Goods shipped out at the reception price, billed higher after."""
        self._lc_two_steps_warehouse(steps=steps)
        product = self.product_fifo
        purchase = self._lc_two_steps_purchase(product, 10.0, 100.0)
        in_move = self._lc_in_move(purchase)
        self._lc_validate(in_move.picking_id, 10.0)
        chain = self._lc_chain(in_move, 10.0)
        out_move = self._lc_deliver(product, 4.0)
        self._lc_assert(out_move, 400.0, "delivery before the bill")

        self._bill_at(purchase, 120.0)

        self._lc_assert(in_move, 1200.0, "reception move")
        for move in chain:
            self._lc_assert(move, 1200.0, "reception chain move")
        self._lc_assert(out_move, 480.0, "delivery after the bill")
        self.assertAlmostEqual(
            self._lc_stock_value(product),
            720.0,
            2,
            "what is left on hand carries the rest of the difference",
        )

    def test_price_difference_two_steps_delivered_before_bill(self):
        self._price_difference_delivered_before_bill("two_steps")

    def test_price_difference_three_steps_delivered_before_bill(self):
        self._price_difference_delivered_before_bill("three_steps")
