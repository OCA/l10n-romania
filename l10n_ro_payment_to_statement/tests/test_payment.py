# ©  2015-2021 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo.tests import tagged

from .common import TestPaymenttoStatement


@tagged("post_install", "-at_install")
class TestPaymentSequence(TestPaymenttoStatement):
    """Numbers the payments of a cash journal take from its sequences."""

    def test_customer_cash_in(self):
        payment = self._post_payment(
            payment_type="inbound", partner_type="customer", amount=150.0
        )
        self.assertEqual(payment.name, self.cash_journal.code + "CH000001")

    def test_customer_cash_out(self):
        payment = self._post_payment(
            payment_type="outbound", partner_type="customer", amount=150.0
        )
        self.assertEqual(payment.name, self.cash_journal.code + "DP000001")

    def test_supplier_cash_in(self):
        payment = self._post_payment(
            payment_type="inbound", partner_type="supplier", amount=150.0
        )
        self.assertEqual(payment.name, self.cash_journal.code + "DI000001")

    def test_supplier_cash_out(self):
        payment = self._post_payment(
            payment_type="outbound", partner_type="supplier", amount=150.0
        )
        self.assertEqual(payment.name, self.cash_journal.code + "000001")

    def test_journal_sequence_can_be_replaced(self):
        sequence = self.env["ir.sequence"].create(
            {
                "name": "Seq",
                "code": "TT",
                "implementation": "no_gap",
                "prefix": "TT",
                "padding": 6,
                "company_id": self.env.company.id,
            }
        )
        self.cash_journal.l10n_ro_journal_sequence_id = sequence.id
        payment = self._post_payment(
            payment_type="outbound", partner_type="supplier", amount=150.0
        )
        self.assertEqual(payment.name, "TT000001")

    def test_numbers_follow_each_other(self):
        first = self._post_payment(amount=10.0)
        second = self._post_payment(amount=20.0)
        self.assertEqual(first.name, self.cash_journal.code + "CH000001")
        self.assertEqual(second.name, self.cash_journal.code + "CH000002")
