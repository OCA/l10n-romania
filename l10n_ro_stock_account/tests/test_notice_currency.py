# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Reception on notice (`picking.l10n_ro_notice`) for a purchase in foreign currency.

Characterisation tests: they pin the CURRENT behaviour of the 4081 pivot (Suppliers -
uninvoiced receipts) so that any change to it is visible, and they mark a gap rather
than
endorsing it.

The gap: per OMFP 1802/2014, the function of account 408 lists on its debit side "the
value
of the invoices received (401)" plus the FAVOURABLE exchange rate differences "recorded
when
the invoice is received" (765), and on its credit side "the value of the goods purchased
(371, 301, 302, ...)" plus the UNFAVOURABLE ones (665). So the exchange rate difference
is due
when the invoice arrives, and the price difference goes through 408 against 371.

This module does neither: the 4081 line of the notice entry carries no foreign currency
amount,
nothing ever settles 4081, and `_get_value_from_bill` is not overridden - so the rate
delta is
left as a silent balance on 4081 while the stock ledger and account 371 drift apart. The
`reconcile` flag on 4081 is irrelevant here, since no reconciliation is ever attempted.
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

    def _exchange_moves(self):
        return self._lines(self.acc_765 | self.acc_665).move_id

    # ------------------------------------------------------------------
    # 1. Structure of the notice reception entry
    # ------------------------------------------------------------------

    def test_notice_reception_posts_371_4081_without_currency(self):
        """The notice reception books 371 = 4081 at the receipt rate, but the 4081
        line carries NO foreign currency - the order currency is lost."""
        purchase = self._purchase()
        move = self._receive_on_notice(purchase)

        self.assertEqual(move.l10n_ro_move_type, "reception_notice")
        entry = move.account_move_id
        self.assertTrue(entry, "The notice reception must generate an accounting entry")
        line_371 = entry.line_ids.filtered(
            lambda line: line.account_id == self.account_valuation
        )
        line_4081 = entry.line_ids.filtered(
            lambda line: line.account_id == self.acc_4081
        )
        self.assertAlmostEqual(sum(line_371.mapped("balance")), 5000.0)
        self.assertAlmostEqual(sum(line_4081.mapped("balance")), -5000.0)
        self.assertEqual(
            line_4081.currency_id,
            self.company_currency,
            "4081 is booked in company currency only - the foreign amount is lost",
        )

    def test_bill_line_routed_to_4081(self):
        purchase = self._purchase()
        self._receive_on_notice(purchase)
        self._set_rate(self.date_bill, 4.0)
        invoice = self._bill(purchase)

        self.assertEqual(invoice.currency_id, self.eur)
        self.assertEqual(
            invoice.invoice_line_ids.account_id,
            self.acc_4081,
            "The bill line of a notice reception must be routed to 4081",
        )
        self.assertAlmostEqual(
            invoice.invoice_line_ids.balance, 4000.0, msg="Bill at its own rate (1:4)"
        )

    # ------------------------------------------------------------------
    # 2. No automatic exchange difference on this path
    # ------------------------------------------------------------------

    def test_no_exchange_difference_even_when_4081_is_reconcilable(self):
        """4081 is reconcilable by default in the Romanian chart, but this module never
        reconciles it: no exchange difference is recognised and the rate delta stays as
        a balance on 4081.

        GAP: OMFP 1802/2014 requires the exchange rate difference on 408 to be recorded
        when
        the invoice is received (765 favourable / 665 unfavourable). This test pins the
        current
        behaviour so a fix is visible as a change here."""
        self.assertTrue(self.acc_4081.reconcile, "4081 is reconcilable in the RO chart")
        purchase = self._purchase()
        self._receive_on_notice(purchase)
        self._set_rate(self.date_bill, 4.0)
        invoice = self._bill(purchase)

        self.assertFalse(
            self._exchange_moves(),
            "No exchange difference can be generated without reconciliation",
        )
        self.assertFalse(
            invoice.invoice_line_ids.matched_credit_ids,
            "The bill line is not reconciled against the notice entry",
        )
        self.assertAlmostEqual(
            self._balance(self.acc_4081),
            -1000.0,
            msg="The rate delta (5000 - 4000) is left as a credit balance on 4081",
        )

    def test_reconcile_flag_makes_no_difference(self):
        """Turning the `reconcile` flag off on 4081 changes nothing on this path:
        the outcome is identical because nothing is ever reconciled."""
        self.acc_4081.reconcile = False
        purchase = self._purchase()
        self._receive_on_notice(purchase)
        self._set_rate(self.date_bill, 4.0)
        invoice = self._bill(purchase)

        self.assertEqual(invoice.invoice_line_ids.account_id, self.acc_4081)
        self.assertFalse(self._exchange_moves())
        self.assertAlmostEqual(self._balance(self.acc_4081), -1000.0)

    def test_no_residual_when_rate_unchanged(self):
        """Control: same rate on receipt and bill - 4081 nets to zero on its own,
        without any reconciliation."""
        purchase = self._purchase()
        self._receive_on_notice(purchase)
        invoice = self._bill(purchase, date=self.date_recv)

        self.assertAlmostEqual(invoice.invoice_line_ids.balance, 5000.0)
        self.assertFalse(self._exchange_moves())
        self.assertAlmostEqual(self._balance(self.acc_4081), 0.0)

    def test_purchase_in_company_currency_nets_to_zero(self):
        """Control: purchase in company currency - no rate exposure at all."""
        purchase = self._purchase(currency=self.company_currency)
        self._receive_on_notice(purchase)
        self._set_rate(self.date_bill, 4.0)
        self._bill(purchase)

        self.assertFalse(self._exchange_moves())
        self.assertAlmostEqual(self._balance(self.acc_4081), 0.0)

    def test_no_notice_no_4081(self):
        """Control: without the notice flag the reception does not use 4081."""
        purchase = self._purchase()
        move = self._receive_on_notice(purchase, notice=False)
        invoice = self._bill(purchase)

        self.assertEqual(move.l10n_ro_move_type, "reception")
        self.assertNotEqual(invoice.invoice_line_ids.account_id, self.acc_4081)
        self.assertAlmostEqual(self._balance(self.acc_4081), 0.0)

    # ------------------------------------------------------------------
    # 3. Manual reconciliation of the 4081 pivot
    # ------------------------------------------------------------------

    def test_manual_reconciliation_leaves_residual_in_company_currency(self):
        """Reconciling 4081 by hand does not settle the pivot: because the notice line
        has no foreign currency amount, the reconciliation is done in company currency
        and the rate delta is left over instead of being booked to 765/665.

        GAP: there is no way for the accountant to settle 4081 on this path, by hand or
        otherwise. Keeping the order currency on the 4081 line would let the
        reconciliation
        recognise the difference on 765/665 by itself."""
        purchase = self._purchase()
        move = self._receive_on_notice(purchase)
        self._set_rate(self.date_bill, 4.0)
        invoice = self._bill(purchase)

        notice_line = move.account_move_id.line_ids.filtered(
            lambda line: line.account_id == self.acc_4081
        )
        bill_line = invoice.invoice_line_ids
        (notice_line + bill_line).reconcile()

        self.assertAlmostEqual(
            self._balance(self.acc_4081),
            -1000.0,
            msg="4081 still carries the rate delta after a manual reconciliation",
        )
        self.assertAlmostEqual(
            notice_line.amount_residual,
            -1000.0,
            msg="The notice line stays partially reconciled for the rate delta",
        )

    # ------------------------------------------------------------------
    # 4. Stock valuation vs accounting
    # ------------------------------------------------------------------

    def test_stock_value_follows_bill_rate_while_371_keeps_receipt_rate(self):
        """The stock layer revalues the move at the bill rate (no `_get_value_from_bill`
        override on this path), while the accounting entry keeps the receipt rate: the
        stock ledger and account 371 diverge by the rate delta.

        GAP: inventory is a non-monetary asset and must not be revalued for exchange
        rate
        movements (IAS 21 / OMFP 1802); the stock ledger and account 371 should
        agree."""
        purchase = self._purchase()
        move = self._receive_on_notice(purchase)
        self._set_rate(self.date_bill, 4.0)
        self._bill(purchase)

        self.assertAlmostEqual(
            move.value, 4000.0, msg="Stock layer follows the bill rate"
        )
        self.assertAlmostEqual(
            self._balance(self.account_valuation),
            5000.0,
            msg="Account 371 keeps the receipt rate",
        )
