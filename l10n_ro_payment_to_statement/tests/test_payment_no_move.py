# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command
from odoo.tests import tagged

from .common import TestPaymenttoStatement


@tagged("post_install", "-at_install")
class TestPaymentNoMove(TestPaymenttoStatement):
    def setUp(self):
        super().setUp()
        self.env.company.l10n_ro_accounting = True
        self.partner_a = self.env["res.partner"].create({"name": "test"})

    def test_invoice_paid_with_cash_payment_reconciles_statement_line(self):
        # An invoice paid through the register payment wizard on a cash
        # journal gets a payment without its own move_id: the accounting
        # entry lives on the generated l10n_ro_statement_line_id instead.
        # The invoice must be reconciled against that statement line's move.
        #
        # Accounting entries:
        #   invoice:                   411 = %        121 lei
        #                                    707      100 lei
        #                                    4427     21 lei
        #   payment:           no journal entry of its own (empty move_id)
        #   payment.l10n_ro_statement_line_id: 
        #                              531 = 411      121 lei

        cash_journal = self.env["account.journal"].search(
            [("type", "=", "cash"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        cash_journal.inbound_payment_method_line_ids.payment_account_id = False

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2015-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test line",
                            "quantity": 1,
                            "price_unit": 100.0,
                            "tax_ids": [Command.set(self.tax_sale_a.ids)],
                        }
                    )
                ],
            }
        )
        invoice.action_post()

        payment_register = (
            self.env["account.payment.register"]
            .with_context(
                active_model="account.move",
                active_ids=invoice.ids,
            )
            .create(
                {
                    "journal_id": cash_journal.id,
                    "payment_method_line_id": cash_journal.inbound_payment_method_line_ids[
                        0
                    ].id,
                }
            )
        )
        payment = payment_register._create_payments()

        self.assertFalse(payment.move_id)
        self.assertTrue(payment.l10n_ro_statement_line_id)
        self.assertEqual(invoice.payment_state, "paid")

        receivable_line = invoice.line_ids.filtered(
            lambda line: line.account_type == "asset_receivable"
        )
        self.assertTrue(receivable_line.reconciled)
        matched_move = (
            receivable_line.matched_credit_ids.credit_move_id.move_id
            | receivable_line.matched_debit_ids.debit_move_id.move_id
        )
        self.assertEqual(matched_move, payment.l10n_ro_statement_line_id.move_id)

        # the statement line's counterpart line must use the invoice's own
        # receivable account (411), not the journal's suspense account,
        # since it is reconciled directly against the invoice: the
        # register payment wizard reassigns it away from the suspense
        # account, so _seek_for_lines() now reports it as an "other" line.
        _liquidity_lines, suspense_lines, other_lines = (
            payment.l10n_ro_statement_line_id._seek_for_lines()
        )
        self.assertFalse(suspense_lines)
        self.assertEqual(other_lines.account_id, receivable_line.account_id)
