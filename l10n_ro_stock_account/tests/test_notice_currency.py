# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Reception on notice (`picking.l10n_ro_notice`) for a purchase in a foreign currency.

The 408 pivot (Suppliers - uninvoiced receipts) is an estimated liability: a monetary
item.
Per OMFP 1802/2014, account 408 is debited with "the value of the invoices received
(401)" and
with the favourable exchange rate differences "recorded when the invoice is received"
(765), and
credited with the unfavourable ones (665). Inventory, being a non-monetary asset, is not
revalued
for exchange rate movements (IAS 21).

So the reception keeps the order currency on the 408 leg, and when the invoice arrives
the rate
delta on the received quantity goes to 765/665 while the stock value stays at the
reception rate.
No reconciliation is involved, which is why 408 does not need to be a reconcilable
account.
"""

from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import TestROStockCommon


@tagged("post_install", "-at_install")
class TestNoticeCurrency(TestROStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_currency = cls.env.company.currency_id
        cls.acc_4081 = cls.env.company.l10n_ro_property_stock_picking_payable_account_id
        cls.acc_765 = cls.env.company.income_currency_exchange_account_id
        cls.acc_665 = cls.env.company.expense_currency_exchange_account_id

        # Receipt rate: 1 EUR = 5 RON. Cleared first so the test does not depend
        # on rates already present in the database.
        cls.date_recv = fields.Date.today()
        cls.date_bill = cls.date_recv + timedelta(days=1)
        cls.env["res.currency.rate"].search(
            [
                ("currency_id", "=", cls.eur.id),
                ("company_id", "in", (cls.env.company.root_id.id, False)),
            ]
        ).unlink()
        cls._set_rate(cls.date_recv - timedelta(days=30), 5.0)

        cls.supplier_1.property_purchase_currency_id = cls.eur.id
        cls.picking_type_in = cls.location.warehouse_id.in_type_id

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

    def _purchase(self, qty=10.0, price=100.0, currency=None):
        purchase = self.env["purchase.order"].create(
            {
                "partner_id": self.supplier_1.id,
                "currency_id": (currency or self.eur).id,
                "picking_type_id": self.picking_type_in.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_fifo.id,
                            "product_qty": qty,
                            "price_unit": price,
                        },
                    )
                ],
            }
        )
        purchase.button_confirm()
        return purchase

    def _receive_on_notice(self, purchase, notice=True):
        picking = purchase.picking_ids[:1]
        picking.l10n_ro_notice = notice
        picking.move_ids._set_quantity_done(purchase.order_line[:1].product_qty)
        picking.move_ids.picked = True
        picking.button_validate()
        if picking.state == "assigned":
            picking._action_done()
        return picking.move_ids[:1]

    def _bill(self, purchase, price=None, date=None):
        action = purchase.action_create_invoice()
        invoice = self.env["account.move"].browse(action["res_id"])
        invoice.invoice_date = date or self.date_bill
        if price is not None:
            invoice.invoice_line_ids.price_unit = price
        invoice.action_post()
        return invoice

    def _lines(self, accounts):
        return self.env["account.move.line"].search(
            [
                ("account_id", "in", accounts.ids),
                ("parent_state", "=", "posted"),
                ("company_id", "=", self.env.company.id),
            ]
        )

    def _balance(self, accounts):
        return sum(self._lines(accounts).mapped("balance"))

    def _exchange_lines(self):
        return self._lines(self.acc_765 | self.acc_665)

    # ------------------------------------------------------------------
    # 1. Structure of the notice reception entry
    # ------------------------------------------------------------------

    def test_notice_reception_keeps_order_currency_on_408(self):
        """The notice reception books 371 = 408 at the reception rate, and the 408 leg
        keeps
        the order currency so the rate difference stays computable."""
        purchase = self._purchase()
        move = self._receive_on_notice(purchase)

        self.assertEqual(move.l10n_ro_move_type, "reception_notice")
        entry = move.account_move_id
        self.assertTrue(entry, "The notice reception must generate an accounting entry")
        line_371 = entry.line_ids.filtered(
            lambda line: line.account_id == self.account_valuation
        )
        line_408 = entry.line_ids.filtered(
            lambda line: line.account_id == self.acc_4081
        )
        self.assertAlmostEqual(sum(line_371.mapped("balance")), 5000.0)
        self.assertAlmostEqual(sum(line_408.mapped("balance")), -5000.0)
        self.assertEqual(
            line_408.currency_id, self.eur, "408 must keep the order currency"
        )
        self.assertAlmostEqual(
            line_408.amount_currency,
            -1000.0,
            msg="408 = 1000 units of foreign currency",
        )
        self.assertEqual(
            line_371.currency_id,
            self.company_currency,
            "the stock leg stays in company currency, at the reception rate",
        )

    def test_bill_line_routed_to_408(self):
        purchase = self._purchase()
        self._receive_on_notice(purchase)
        self._set_rate(self.date_bill, 4.0)
        invoice = self._bill(purchase)

        self.assertEqual(invoice.currency_id, self.eur)
        self.assertEqual(
            invoice.invoice_line_ids.account_id,
            self.acc_4081,
            "The bill line of a notice reception must be routed to 408",
        )
        self.assertAlmostEqual(
            invoice.invoice_line_ids.balance, 4000.0, msg="Bill at its own rate (1:4)"
        )

    # ------------------------------------------------------------------
    # 2. Exchange rate difference when the invoice is received
    # ------------------------------------------------------------------

    def test_favourable_rate_difference_goes_to_765(self):
        """Lower rate on the invoice (1:4): Dr 408 / Cr 765, the pivot closes and the
        stock
        value stays at the reception rate."""
        purchase = self._purchase()
        move = self._receive_on_notice(purchase)
        self._set_rate(self.date_bill, 4.0)
        self._bill(purchase)

        self.assertAlmostEqual(
            self._balance(self.acc_765),
            -1000.0,
            msg="favourable difference of 1000 on 765",
        )
        self.assertAlmostEqual(self._balance(self.acc_665), 0.0)
        self.assertAlmostEqual(
            self._balance(self.acc_4081), 0.0, msg="the 408 pivot must close"
        )
        self.assertAlmostEqual(
            self._balance(self.account_valuation),
            5000.0,
            msg="inventory is not revalued for the rate movement",
        )
        self.assertAlmostEqual(
            move.value,
            self._balance(self.account_valuation),
            msg="the stock ledger must agree with the stock account",
        )

    def test_unfavourable_rate_difference_goes_to_665(self):
        """Higher rate on the invoice (1:6): Cr 408 / Dr 665, the pivot closes."""
        purchase = self._purchase()
        move = self._receive_on_notice(purchase)
        self._set_rate(self.date_bill, 6.0)
        self._bill(purchase)

        self.assertAlmostEqual(
            self._balance(self.acc_665),
            1000.0,
            msg="unfavourable difference of 1000 on 665",
        )
        self.assertAlmostEqual(self._balance(self.acc_765), 0.0)
        self.assertAlmostEqual(self._balance(self.acc_4081), 0.0)
        self.assertAlmostEqual(self._balance(self.account_valuation), 5000.0)
        self.assertAlmostEqual(move.value, self._balance(self.account_valuation))

    def test_no_rate_difference_when_rate_unchanged(self):
        """Same rate on reception and invoice: nothing to recognise, the pivot closes on
        its
        own."""
        purchase = self._purchase()
        self._receive_on_notice(purchase)
        invoice = self._bill(purchase, date=self.date_recv)

        self.assertAlmostEqual(invoice.invoice_line_ids.balance, 5000.0)
        self.assertFalse(self._exchange_lines())
        self.assertAlmostEqual(self._balance(self.acc_4081), 0.0)

    def test_no_rate_difference_on_purchase_in_company_currency(self):
        """Control: purchase in company currency - no rate exposure at all."""
        purchase = self._purchase(currency=self.company_currency)
        move = self._receive_on_notice(purchase)
        self._set_rate(self.date_bill, 4.0)
        self._bill(purchase)

        entry_408 = move.account_move_id.line_ids.filtered(
            lambda line: line.account_id == self.acc_4081
        )
        self.assertEqual(entry_408.currency_id, self.company_currency)
        self.assertFalse(self._exchange_lines())
        self.assertAlmostEqual(self._balance(self.acc_4081), 0.0)

    def test_no_notice_no_408(self):
        """Control: without the notice flag the reception does not use 408."""
        purchase = self._purchase()
        move = self._receive_on_notice(purchase, notice=False)
        invoice = self._bill(purchase)

        self.assertEqual(move.l10n_ro_move_type, "reception")
        self.assertNotEqual(invoice.invoice_line_ids.account_id, self.acc_4081)
        self.assertAlmostEqual(self._balance(self.acc_4081), 0.0)

    # ------------------------------------------------------------------
    # 3. The pivot does not rely on reconciliation
    # ------------------------------------------------------------------

    def test_settlement_works_without_reconcile_flag(self):
        """Account 408 does not need to be reconcilable: the pivot closes by
        document."""
        self.acc_4081.reconcile = False
        purchase = self._purchase()
        self._receive_on_notice(purchase)
        self._set_rate(self.date_bill, 4.0)
        self._bill(purchase)

        self.assertAlmostEqual(self._balance(self.acc_765), -1000.0)
        self.assertAlmostEqual(self._balance(self.acc_4081), 0.0)

    def test_no_reconciliation_is_performed_on_408(self):
        """Nothing reconciles 408 - the closing is driven by documents, not by
        matching."""
        purchase = self._purchase()
        self._receive_on_notice(purchase)
        self._set_rate(self.date_bill, 4.0)
        self._bill(purchase)

        lines = self._lines(self.acc_4081)
        self.assertFalse(lines.matched_debit_ids | lines.matched_credit_ids)

    # ------------------------------------------------------------------
    # 4. Rate difference versus price difference
    # ------------------------------------------------------------------

    def test_rate_difference_only_on_the_received_quantity(self):
        """Invoiced above the order (1100 instead of 1000 units of currency) at a
        different
        rate: only the received part carries a rate difference. The surplus is a price
        difference, whose liability arises at the invoice date, so it is valued at the
        invoice
        rate and left on 408 - settling it is out of scope here."""
        purchase = self._purchase()
        self._receive_on_notice(purchase)
        self._set_rate(self.date_bill, 4.0)
        invoice = self._bill(purchase, price=110.0)

        self.assertAlmostEqual(invoice.invoice_line_ids.balance, 4400.0)
        self.assertAlmostEqual(
            self._balance(self.acc_765),
            -1000.0,
            msg="rate difference on the received 1000",
        )
        self.assertAlmostEqual(
            self._balance(self.acc_4081),
            400.0,
            msg="the surplus of 100 at the invoice rate remains a price difference",
        )

    def test_partial_bill_leaves_the_uninvoiced_part_on_408(self):
        """Partial invoicing: 408 keeps the value of the quantity not yet invoiced, at
        the
        reception rate, and the rate difference covers only what was invoiced."""
        purchase = self._purchase()
        self._receive_on_notice(purchase)
        self._set_rate(self.date_bill, 4.0)
        action = purchase.action_create_invoice()
        invoice = self.env["account.move"].browse(action["res_id"])
        invoice.invoice_date = self.date_bill
        invoice.invoice_line_ids.quantity = 4.0
        invoice.action_post()

        self.assertAlmostEqual(
            self._balance(self.acc_765), -400.0, msg="rate difference on 4 units only"
        )
        self.assertAlmostEqual(
            self._balance(self.acc_4081), -3000.0, msg="6 units x 500 still pending"
        )
        self.assertAlmostEqual(self._balance(self.account_valuation), 5000.0)
