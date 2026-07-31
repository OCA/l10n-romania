# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Price difference and exchange rate difference on the 408 pivot, together.

With `l10n_ro_stock_acc_price_diff` enabled, both mechanisms look at the gap between a
reception on notice and the supplier invoice. They must not book the same delta twice:
the exchange rate difference goes to 765/665 and the price difference is what is
left on 408 afterwards, so the pivot closes and inventory is not retranslated.
"""

from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon


@tagged("post_install", "-at_install")
class TestNoticeCurrencyPriceDifference(TestROStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.l10n_ro_stock_acc_price_diff = True
        cls.company_currency = cls.env.company.currency_id
        cls.acc_4081 = cls.env.company.l10n_ro_property_stock_picking_payable_account_id
        cls.acc_765 = cls.env.company.income_currency_exchange_account_id
        cls.acc_665 = cls.env.company.expense_currency_exchange_account_id

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
        return cls.env["res.currency.rate"].create(
            {
                "currency_id": cls.eur.id,
                "name": date,
                "company_id": cls.env.company.root_id.id,
                "inverse_company_rate": inverse_rate,
            }
        )

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

    def _receive_on_notice(self, purchase):
        picking = purchase.picking_ids[:1]
        picking.l10n_ro_notice = True
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
        # the confirmation dialog is bypassed, as in the other tests of this module
        invoice.with_context(l10n_ro_approved_price_difference=True).action_post()
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

    def test_rate_only_is_not_taken_for_a_price_difference(self):
        """Same amount in foreign currency, different rate: the whole delta is
        an exchange rate difference on 765, nothing is capitalised, 408 closes."""
        purchase = self._purchase()
        self._receive_on_notice(purchase)
        self._set_rate(self.date_bill, 4.0)
        self._bill(purchase)

        self.assertAlmostEqual(self._balance(self.acc_765), -1000.0)
        self.assertAlmostEqual(
            self._balance(self.acc_4081), 0.0, msg="the 408 pivot must close"
        )
        self.assertAlmostEqual(
            self._balance(self.account_valuation),
            5000.0,
            msg="inventory keeps the reception rate - the delta is not capitalised",
        )

    def test_price_only_is_capitalised(self):
        """Same rate, higher price: no rate difference, the price difference is
        capitalised and 408 closes."""
        purchase = self._purchase()
        self._receive_on_notice(purchase)
        self._bill(purchase, price=110.0, date=self.date_recv)

        self.assertFalse(self._lines(self.acc_765 | self.acc_665))
        self.assertAlmostEqual(self._balance(self.acc_4081), 0.0)
        self.assertAlmostEqual(
            self._balance(self.account_valuation),
            5500.0,
            msg="the price difference adjusts inventory",
        )

    def test_price_and_rate_are_split_and_408_closes(self):
        """Both differ: the rate part goes to 765 for the received quantity, the surplus
        is capitalised at the invoice rate, and the pivot closes."""
        purchase = self._purchase()
        self._receive_on_notice(purchase)
        self._set_rate(self.date_bill, 4.0)
        self._bill(purchase, price=110.0)

        self.assertAlmostEqual(
            self._balance(self.acc_765),
            -1000.0,
            msg="rate difference on the received 1000",
        )
        self.assertAlmostEqual(
            self._balance(self.acc_4081), 0.0, msg="the 408 pivot must close"
        )
        self.assertAlmostEqual(
            self._balance(self.account_valuation),
            5400.0,
            msg="5000 at the reception rate plus 100 surplus at the invoice rate",
        )
