# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Reception on notice of one purchase order holding the same product on two lines.

A picking books a single journal entry for all its stock moves, so the reception
entry holds one 371 / 408 pair per purchase line, all on the same product. Each
bill line must be compared only with the 408 line of its own purchase line -
whatever the quantities, prices, units of measure or currency - otherwise it
takes the other line's value as received and the price difference dialog, the
price difference itself and the exchange rate difference are all wrong.
"""

from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon


@tagged("post_install", "-at_install")
class TestNoticeSameProductLines(TestROStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.l10n_ro_stock_acc_price_diff = True
        cls.company_currency = cls.env.company.currency_id
        cls.acc_4081 = cls.env.company.l10n_ro_property_stock_picking_payable_account_id
        cls.acc_765 = cls.env.company.income_currency_exchange_account_id
        cls.acc_665 = cls.env.company.expense_currency_exchange_account_id
        cls.picking_type_in = cls.location.warehouse_id.in_type_id

        # Receipt rate: 1 EUR = 5 RON, cleared first so the test does not
        # depend on rates already present in the database.
        cls.date_recv = fields.Date.today()
        cls.date_bill = cls.date_recv + timedelta(days=1)
        cls.env["res.currency.rate"].search(
            [
                ("currency_id", "=", cls.eur.id),
                ("company_id", "in", (cls.env.company.root_id.id, False)),
            ]
        ).unlink()
        cls._set_rate(cls.date_recv - timedelta(days=30), 5.0)

        # Keep the purchase line's UoM on the stock move: the reception is then
        # really encoded in boxes, not normalised back to units.
        cls.env["ir.config_parameter"].sudo().set_param("stock.propagate_uom", "1")
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.uom_box10 = cls.env["uom.uom"].create(
            {
                "name": "Box of 10",
                "relative_uom_id": cls.uom_unit.id,
                "relative_factor": 10.0,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Product FIFO on two lines",
                "is_storable": True,
                "categ_id": cls.category_marfa_fifo.id,
                "purchase_method": "receive",
                "uom_id": cls.uom_unit.id,
                "uom_ids": [(6, 0, [cls.uom_box10.id])],
            }
        )

    @classmethod
    def _set_rate(cls, date, inverse_rate):
        """`inverse_rate` units of company currency for 1 unit of EUR."""
        return cls.env["res.currency.rate"].create(
            {
                "currency_id": cls.eur.id,
                "name": date,
                "company_id": cls.env.company.root_id.id,
                "inverse_company_rate": inverse_rate,
            }
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _purchase_on_notice(self, lines, currency=None):
        """Confirm a purchase of ``self.product`` with one line per
        ``(qty, price, uom)`` and receive it all on notice in one picking.
        Returns the purchase lines in the given order."""
        purchase = self.env["purchase.order"].create(
            {
                "partner_id": self.supplier_1.id,
                "currency_id": (currency or self.company_currency).id,
                "picking_type_id": self.picking_type_in.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": qty,
                            "product_uom_id": (uom or self.uom_unit).id,
                            "price_unit": price,
                        },
                    )
                    for qty, price, uom in lines
                ],
            }
        )
        purchase.button_confirm()
        picking = purchase.picking_ids
        self.assertEqual(len(picking), 1)
        self.assertEqual(
            len(picking.move_ids), len(lines), "one stock move per purchase line"
        )
        picking.l10n_ro_notice = True
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.move_ids.picked = True
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        self.assertEqual(
            len(picking.move_ids.account_move_id),
            1,
            "the reception books a single entry for the whole picking",
        )
        return purchase.order_line

    def _bill(self, po_lines, prices, quantities=None, date=None):
        """Draft bill for the purchase, with the price (and optionally the
        quantity) of each purchase line set as given, in the purchase line UoM."""
        purchase = po_lines.order_id
        action = purchase.action_create_invoice()
        invoice = self.env["account.move"].browse(action["res_id"])
        invoice.invoice_date = date or self.date_recv
        for po_line, price in zip(po_lines, prices, strict=True):
            inv_line = invoice.invoice_line_ids.filtered(
                lambda line, po_line=po_line: line.purchase_line_id == po_line
            )
            inv_line.price_unit = price
            if quantities:
                inv_line.quantity = quantities[po_lines.ids.index(po_line.id)]
        return invoice

    def _diffs(self, invoice, po_lines):
        """What the price difference dialog would show, as a list of
        ``(index of the purchase line, value_diff, qty_diff)``."""
        res = []
        for diff in invoice._get_l10n_ro_price_differences().get(invoice.id, []):
            inv_line = self.env["account.move.line"].browse(diff["invoice_line_id"])
            res.append(
                (
                    po_lines.ids.index(inv_line.purchase_line_id.id),
                    diff["value_diff"],
                    diff["qty_diff"],
                )
            )
        return sorted(res)

    def _post(self, invoice):
        # the confirmation dialog is bypassed, as in the other tests of this module
        invoice.with_context(l10n_ro_approved_price_difference=True).action_post()
        self.assertEqual(invoice.state, "posted")

    def _balance(self, accounts):
        return sum(
            self.env["account.move.line"]
            .search(
                [
                    ("account_id", "in", accounts.ids),
                    ("parent_state", "=", "posted"),
                    ("company_id", "=", self.env.company.id),
                ]
            )
            .mapped("balance")
        )

    def _assert_balances(self, stock, pivot=0.0, exchange=0.0):
        self.assertAlmostEqual(self._balance(self.account_valuation), stock)
        self.assertAlmostEqual(
            self._balance(self.acc_4081), pivot, msg="408 pivot balance"
        )
        self.assertAlmostEqual(
            self._balance(self.acc_765 | self.acc_665),
            exchange,
            msg="exchange rate difference (765 credit < 0, 665 debit > 0)",
        )

    # ------------------------------------------------------------------
    # Company currency
    # ------------------------------------------------------------------

    def test_reception_lines_carry_their_purchase_line(self):
        """Each 371 / 408 pair of the reception entry carries its purchase
        line, which is what tells apart two lines on the same product."""
        po_lines = self._purchase_on_notice([(10, 800, None), (5, 900, None)])
        entry = po_lines.move_ids.account_move_id
        self.assertEqual(
            sorted(
                (line.purchase_line_id.id, line.balance)
                for line in entry.line_ids
                if line.account_id == self.acc_4081
            ),
            sorted([(po_lines[0].id, -8000.0), (po_lines[1].id, -4500.0)]),
        )
        self.assertEqual(
            sorted(
                (line.purchase_line_id.id, line.balance)
                for line in entry.line_ids
                if line.account_id == self.account_valuation
            ),
            sorted([(po_lines[0].id, 8000.0), (po_lines[1].id, 4500.0)]),
        )

    def test_reception_entry_is_not_a_bill_of_the_purchase(self):
        """The purchase line on the stock entry does not count as invoiced."""
        po_lines = self._purchase_on_notice([(10, 800, None), (5, 900, None)])
        self.assertEqual(po_lines.mapped("qty_invoiced"), [0.0, 0.0])
        self.assertEqual(po_lines.mapped("qty_to_invoice"), [10.0, 5.0])

    def test_difference_on_one_line_only(self):
        """10 x 800 billed at 880, 5 x 900 billed at 900: only the first line
        shows a difference, of 10 x 80."""
        po_lines = self._purchase_on_notice([(10, 800, None), (5, 900, None)])
        invoice = self._bill(po_lines, [880, 900])
        self.assertEqual(self._diffs(invoice, po_lines), [(0, 800.0, 0.0)])

        self._post(invoice)
        self._assert_balances(stock=8000 + 800 + 4500)

    def test_difference_on_both_lines_opposite_signs(self):
        """10 x 800 billed at 880 (+800), 5 x 900 billed at 850 (-250)."""
        po_lines = self._purchase_on_notice([(10, 800, None), (5, 900, None)])
        invoice = self._bill(po_lines, [880, 850])
        self.assertEqual(
            self._diffs(invoice, po_lines), [(0, 800.0, 0.0), (1, -250.0, 0.0)]
        )

        self._post(invoice)
        self._assert_balances(stock=8000 + 800 + 4500 - 250)

    def test_no_difference(self):
        """Both lines billed at the order price: no dialog, no landed cost."""
        po_lines = self._purchase_on_notice([(10, 800, None), (5, 900, None)])
        invoice = self._bill(po_lines, [800, 900])
        self.assertEqual(self._diffs(invoice, po_lines), [])

        self._post(invoice)
        self._assert_balances(stock=12500)
        self.assertFalse(
            self.env["stock.landed.cost"].search(
                [("l10n_ro_cost_type", "=", "price_diff")]
            )
        )

    def test_same_price_different_quantities(self):
        """Same order price on both lines, only the second one billed higher:
        the lines differ only by quantity and must still be told apart."""
        po_lines = self._purchase_on_notice([(10, 800, None), (3, 800, None)])
        invoice = self._bill(po_lines, [800, 850])
        self.assertEqual(self._diffs(invoice, po_lines), [(1, 150.0, 0.0)])

        self._post(invoice)
        self._assert_balances(stock=8000 + 2400 + 150)

    def test_partial_bill_of_one_line(self):
        """4 of the 10 units of the first line billed at 880: the difference is
        on the billed part only, 4 x 80, and the unbilled 6 x 800 stay on 408."""
        po_lines = self._purchase_on_notice([(10, 800, None), (5, 900, None)])
        invoice = self._bill(po_lines, [880, 900], quantities=[4, 5])
        self.assertEqual(self._diffs(invoice, po_lines), [(0, 320.0, 0.0)])

        self._post(invoice)
        self._assert_balances(stock=12500 + 320, pivot=-6 * 800)

    # ------------------------------------------------------------------
    # Units of measure
    # ------------------------------------------------------------------

    def test_lines_in_different_uoms(self):
        """10 units at 800 and 3 boxes of 10 at 9000 (900 / unit), the boxes
        billed at 9500: the difference is 3 x 500, on the box line only."""
        po_lines = self._purchase_on_notice(
            [(10, 800, self.uom_unit), (3, 9000, self.uom_box10)]
        )
        self.assertEqual(
            po_lines[1].move_ids.product_uom, self.uom_box10, "received in boxes"
        )
        invoice = self._bill(po_lines, [800, 9500])
        self.assertEqual(self._diffs(invoice, po_lines), [(1, 1500.0, 0.0)])

        self._post(invoice)
        self._assert_balances(stock=8000 + 27000 + 1500)

    def test_lines_in_different_uoms_both_differ(self):
        """Units billed lower, boxes billed higher, each against its own line."""
        po_lines = self._purchase_on_notice(
            [(10, 800, self.uom_unit), (2, 9000, self.uom_box10)]
        )
        invoice = self._bill(po_lines, [780, 9300])
        self.assertEqual(
            self._diffs(invoice, po_lines), [(0, -200.0, 0.0), (1, 600.0, 0.0)]
        )

        self._post(invoice)
        self._assert_balances(stock=8000 - 200 + 18000 + 600)

    # ------------------------------------------------------------------
    # Foreign currency
    # ------------------------------------------------------------------

    def test_currency_price_and_rate_split_per_line(self):
        """EUR at 5 on reception, 4 on the bill. 10 x 100 EUR billed at 110 and
        5 x 120 EUR billed at 120. The rate difference is booked on 765 for each
        line on its own received value (1000 + 600 EUR x 1), the price
        difference only on the first line, at the bill rate (100 EUR x 4)."""
        po_lines = self._purchase_on_notice(
            [(10, 100, None), (5, 120, None)], currency=self.eur
        )
        self._set_rate(self.date_bill, 4.0)
        invoice = self._bill(po_lines, [110, 120], date=self.date_bill)
        self.assertEqual(self._diffs(invoice, po_lines), [(0, 400.0, 0.0)])

        self._post(invoice)
        self._assert_balances(stock=5000 + 3000 + 400, exchange=-1600.0)

    def test_currency_rate_only(self):
        """Both lines billed at the order price, the rate moved: no price
        difference on either line, only the rate difference on 765."""
        po_lines = self._purchase_on_notice(
            [(10, 100, None), (5, 120, None)], currency=self.eur
        )
        self._set_rate(self.date_bill, 4.0)
        invoice = self._bill(po_lines, [100, 120], date=self.date_bill)
        self.assertEqual(self._diffs(invoice, po_lines), [])

        self._post(invoice)
        self._assert_balances(stock=8000, exchange=-1600.0)

    def test_currency_and_uoms_unfavourable_rate(self):
        """EUR at 5 on reception, 5.5 on the bill (unfavourable, 665).
        10 units x 100 EUR billed at 105 and 2 boxes x 1200 EUR billed at 1250.

        Line 1: received 5000, covered at the bill rate 1000 x 5.5 = 5500,
                rate -500, price 1050 x 5.5 - 5500 = 275.
        Line 2: received 12000, covered 2400 x 5.5 = 13200,
                rate -1200, price 2500 x 5.5 - 13200 = 550.
        """
        po_lines = self._purchase_on_notice(
            [(10, 100, self.uom_unit), (2, 1200, self.uom_box10)],
            currency=self.eur,
        )
        self._set_rate(self.date_bill, 5.5)
        invoice = self._bill(po_lines, [105, 1250], date=self.date_bill)
        self.assertEqual(
            self._diffs(invoice, po_lines), [(0, 275.0, 0.0), (1, 550.0, 0.0)]
        )

        self._post(invoice)
        self._assert_balances(stock=5000 + 12000 + 275 + 550, exchange=1700.0)

    # ------------------------------------------------------------------
    # Posting paths
    # ------------------------------------------------------------------

    def _price_diff_landed_costs(self):
        return self.env["stock.landed.cost"].search(
            [("l10n_ro_cost_type", "=", "price_diff")]
        )

    def test_price_dialog_does_not_post(self):
        """Without approval the price difference dialog is returned and
        nothing is posted nor corrected yet."""
        po_lines = self._purchase_on_notice(
            [(10, 800, None), (3, 9000, self.uom_box10)]
        )
        invoice = self._bill(po_lines, [800, 9500])
        action = invoice.action_post()
        self.assertEqual(action["res_model"], "l10n_ro.price_difference_confirm_dialog")
        self.assertEqual(invoice.state, "draft")
        self.assertFalse(self._price_diff_landed_costs())

    def test_posted_through_confirm_entries_dialog(self):
        """A bill with an unusual amount or a future date is posted by the
        "Confirm Entries" dialog, which calls ``_post`` directly instead of
        ``action_post``: the price difference must be corrected all the same."""
        po_lines = self._purchase_on_notice(
            [(10, 800, None), (3, 9000, self.uom_box10)]
        )
        invoice = self._bill(po_lines, [800, 9500])
        self.assertEqual(self._diffs(invoice, po_lines), [(1, 1500.0, 0.0)])

        self.env["validate.account.move"].create(
            {"move_ids": [(6, 0, invoice.ids)]}
        ).validate_move()
        self.assertEqual(invoice.state, "posted")

        landed_cost = self._price_diff_landed_costs()
        self.assertEqual(len(landed_cost), 1)
        self.assertEqual(landed_cost.state, "done")
        self.assertEqual(
            landed_cost.valuation_adjustment_lines.move_id, po_lines[1].move_ids
        )
        self._assert_balances(stock=8000 + 27000 + 1500)

    def test_future_bill_soft_post_waits(self):
        """A future bill soft-posted is left for the auto-post: no landed cost
        until it is really posted."""
        po_lines = self._purchase_on_notice([(10, 800, None), (5, 900, None)])
        invoice = self._bill(po_lines, [880, 900])
        invoice.date = fields.Date.today() + timedelta(days=10)
        invoice._post(soft=True)
        self.assertEqual(invoice.state, "draft")
        self.assertFalse(self._price_diff_landed_costs())

        # posted now anyway, as "Confirm Entries" does when forced
        invoice.auto_post = "no"
        invoice._post(soft=False)
        self.assertEqual(invoice.state, "posted")
        self.assertEqual(len(self._price_diff_landed_costs()), 1)
