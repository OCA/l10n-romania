# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import Command, fields
from odoo.tests import tagged

from .common import TestNondeductibleCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestNonDeductibleVATP(TestNondeductibleCommon):
    @TestNondeductibleCommon.setup_country("ro")
    def setUp(cls):
        super().setUp()

    def _aml_signature(self, move):
        return sorted(
            (
                line.account_id.code,
                line.display_type,
                line.debit,
                line.credit,
                tuple(sorted(line.tax_tag_ids.mapped("name"))),
            )
            for line in move.line_ids
        )

    def _post_and_pay(self, percent):
        inv = self.vatp_nd_invoice
        inv.invoice_line_ids.deductible_amount = 100 - int(percent)
        inv.action_post()
        invoice_sig = self._aml_signature(inv)
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=inv.ids
        ).create({"payment_date": fields.Date.today()})._create_payments()
        cb_move = inv.tax_cash_basis_created_move_ids
        return inv, invoice_sig, cb_move

    def test_vatp_invoice_defers_non_deductibility(self):
        """On a VAT-on-payment bill the non-deductibility must NOT be split on
        the invoice (deferred to payment): the bill only books the deferred VAT
        on the transition account and the full payable."""
        inv, invoice_sig, _cb = self._post_and_pay("50")

        expected = sorted(
            [
                ("607000", "product", 100.0, 0.0, ()),
                ("442820", "tax", 21.0, 0.0, ()),
                ("401100", "payment_term", 0.0, 121.0, ()),
            ]
        )
        self.assertEqual(invoice_sig, expected)
        # No non-deductible line whatsoever on the invoice.
        self.assertFalse(
            inv.line_ids.filtered(
                lambda line: line.display_type
                in (
                    "non_deductible_product",
                    "non_deductible_product_total",
                    "non_deductible_tax",
                    "non_deductible_tax_ro",
                )
            )
        )

    def test_vatp_cash_basis_50_percent(self):
        """At payment, the cash-basis entry splits the materialized VAT into a
        deductible part (442600, 24 - VAT) and a non-deductible part booked as
        expense (635200, 24_2 - VAT), and likewise splits the base grids."""
        _inv, _sig, cb_move = self._post_and_pay("50")

        expected = sorted(
            [
                ("442830", "product", 0.0, 100.0, ()),
                ("442830", "product", 50.0, 0.0, ("24 - TAX BASE",)),
                ("442830", "product", 50.0, 0.0, ("24_2 - TAX BASE",)),
                ("442820", "tax", 0.0, 21.0, ()),
                ("442600", "tax", 10.5, 0.0, ("24 - VAT",)),
                ("635200", "non_deductible_tax_ro", 10.5, 0.0, ("24_2 - VAT",)),
            ]
        )
        self.assertEqual(len(cb_move.line_ids), 6)
        self.assertEqual(self._aml_signature(cb_move), expected)
        self.assertEqual(
            sum(cb_move.line_ids.mapped("debit")),
            sum(cb_move.line_ids.mapped("credit")),
        )

    def test_vatp_cash_basis_100_percent(self):
        """Fully non-deductible: the whole materialized VAT becomes expense."""
        _inv, _sig, cb_move = self._post_and_pay("100")

        expected = sorted(
            [
                ("442830", "product", 0.0, 100.0, ()),
                ("442830", "product", 100.0, 0.0, ("24_2 - TAX BASE",)),
                ("442820", "tax", 0.0, 21.0, ()),
                ("635200", "non_deductible_tax_ro", 21.0, 0.0, ("24_2 - VAT",)),
            ]
        )
        self.assertEqual(self._aml_signature(cb_move), expected)
        self.assertFalse(
            cb_move.line_ids.filtered(lambda line: line.account_id.code == "442600")
        )
        self.assertEqual(
            sum(cb_move.line_ids.mapped("debit")),
            sum(cb_move.line_ids.mapped("credit")),
        )

    def _create_vatp_bill(self, lines):
        return self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.lxt_partner.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": name,
                            "product_id": self.product_fifo.id,
                            "account_id": self.account_expense.id,
                            "quantity": 1,
                            "price_unit": price,
                            "deductible_amount": deductible,
                            "tax_ids": [Command.set(self.vatp_tax.ids)],
                        }
                    )
                    for name, price, deductible in lines
                ],
            }
        )

    def test_vatp_multiline_partial_payment(self):
        """Two product lines (100 + 200, both 50% non-deductible) paid half:
        the cash-basis split must be proportional to the paid amount."""
        inv = self._create_vatp_bill([("L1", 100.0, 50), ("L2", 200.0, 50)])
        inv.action_post()
        # 300 base + 63 VAT, deferred, full payable.
        self.assertEqual(
            sorted(inv.line_ids.mapped("balance")), [-363.0, 63.0, 100.0, 200.0]
        )

        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=inv.ids
        ).create(
            {"payment_date": fields.Date.today(), "amount": 181.5}
        )._create_payments()

        cb_move = inv.tax_cash_basis_created_move_ids
        expected = sorted(
            [
                ("442830", "product", 0.0, 150.0, ()),
                ("442830", "product", 75.0, 0.0, ("24 - TAX BASE",)),
                ("442830", "product", 75.0, 0.0, ("24_2 - TAX BASE",)),
                ("442820", "tax", 0.0, 31.5, ()),
                ("442600", "tax", 15.75, 0.0, ("24 - VAT",)),
                ("635200", "non_deductible_tax_ro", 15.75, 0.0, ("24_2 - VAT",)),
            ]
        )
        self.assertEqual(self._aml_signature(cb_move), expected)
        self.assertEqual(
            sum(cb_move.line_ids.mapped("debit")),
            sum(cb_move.line_ids.mapped("credit")),
        )

    def test_vatp_mixed_deductibility_same_tax(self):
        """Two lines on the same on-payment tax with different deductibility
        (100 @ 50% non-deductible, 200 fully deductible): the cash-basis split
        is weighted by base, so only 50 of base / 10.5 of VAT is non-deductible."""
        inv = self._create_vatp_bill([("L1", 100.0, 50), ("L2", 200.0, 100)])
        inv.action_post()

        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=inv.ids
        ).create({"payment_date": fields.Date.today()})._create_payments()

        cb_move = inv.tax_cash_basis_created_move_ids
        expected = sorted(
            [
                ("442830", "product", 0.0, 300.0, ()),
                ("442830", "product", 250.0, 0.0, ("24 - TAX BASE",)),
                ("442830", "product", 50.0, 0.0, ("24_2 - TAX BASE",)),
                ("442820", "tax", 0.0, 63.0, ()),
                ("442600", "tax", 52.5, 0.0, ("24 - VAT",)),
                ("635200", "non_deductible_tax_ro", 10.5, 0.0, ("24_2 - VAT",)),
            ]
        )
        self.assertEqual(self._aml_signature(cb_move), expected)
        self.assertEqual(
            sum(cb_move.line_ids.mapped("debit")),
            sum(cb_move.line_ids.mapped("credit")),
        )

    def test_vatp_deductible_and_nondeductible_same_tax_grids(self):
        """A deductible and a non-deductible VAT-on-payment tax sharing the
        very same grids (24 - VAT) coexist on one bill. At payment, only the
        non-deductible tax is split; the deductible one keeps its full VAT on
        442600 (24 - VAT) without any bleeding."""
        inv = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.lxt_partner.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Ded",
                            "product_id": self.product_fifo.id,
                            "account_id": self.account_expense.id,
                            "quantity": 1,
                            "price_unit": 200.0,
                            "deductible_amount": 100,
                            "tax_ids": [Command.set(self.vatp_tax_deductible.ids)],
                        }
                    ),
                    Command.create(
                        {
                            "name": "NonDed",
                            "product_id": self.product_fifo.id,
                            "account_id": self.account_expense.id,
                            "quantity": 1,
                            "price_unit": 100.0,
                            "deductible_amount": 50,
                            "tax_ids": [Command.set(self.vatp_tax.ids)],
                        }
                    ),
                ],
            }
        )
        inv.action_post()
        # Deferred, full payable, no split on the invoice.
        self.assertEqual(inv.amount_total, 363.0)
        self.assertFalse(
            inv.line_ids.filtered(
                lambda line: "non_deductible" in (line.display_type or "")
            )
        )

        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=inv.ids
        ).create({"payment_date": fields.Date.today()})._create_payments()

        cb_move = inv.tax_cash_basis_created_move_ids
        expected = sorted(
            [
                # Deductible tax (200 base / 42 VAT) - kept whole.
                ("442830", "product", 0.0, 200.0, ()),
                ("442830", "product", 200.0, 0.0, ("24 - TAX BASE",)),
                ("442820", "tax", 0.0, 42.0, ()),
                ("442600", "tax", 42.0, 0.0, ("24 - VAT",)),
                # Non-deductible tax (100 base / 21 VAT, 50%) - split.
                ("442830", "product", 0.0, 100.0, ()),
                ("442830", "product", 50.0, 0.0, ("24 - TAX BASE",)),
                ("442830", "product", 50.0, 0.0, ("24_2 - TAX BASE",)),
                ("442820", "tax", 0.0, 21.0, ()),
                ("442600", "tax", 10.5, 0.0, ("24 - VAT",)),
                ("635200", "non_deductible_tax_ro", 10.5, 0.0, ("24_2 - VAT",)),
            ]
        )
        self.assertEqual(self._aml_signature(cb_move), expected)
        self.assertEqual(
            sum(cb_move.line_ids.mapped("debit")),
            sum(cb_move.line_ids.mapped("credit")),
        )
