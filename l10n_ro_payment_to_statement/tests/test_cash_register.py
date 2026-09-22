# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestPaymenttoStatement


@tagged("post_install", "-at_install")
class TestCashRegister(TestPaymenttoStatement):
    """The cash register (statement) a cash journal keeps for its payments."""

    # -- the payment method takes the cash account: one single entry -------

    def test_cash_account_reuses_the_entry_of_the_payment(self):
        self._set_payment_account(self.cash_journal, self.cash_account)
        payment = self._post_payment()

        line = payment.move_id.statement_line_id
        self.assertTrue(line, "the payment did not reach the cash register")
        self.assertEqual(
            line.move_id, payment.move_id, "a second journal entry was created"
        )
        self.assertEqual(line.amount, 100.0)
        self.assertEqual(payment.l10n_ro_statement_line_id, line)
        self.assertEqual(payment.l10n_ro_statement_id, line.statement_id)
        self.assertEqual(line.statement_id.journal_id, self.cash_journal)
        self.assertEqual(line.statement_id.date, fields.Date.to_date("2024-01-15"))

    def test_cash_account_line_needs_no_reconciliation(self):
        self._set_payment_account(self.cash_journal, self.cash_account)
        payment = self._post_payment()

        line = payment.move_id.statement_line_id
        _liquidity, suspense, _other = line._seek_for_lines()
        self.assertFalse(suspense, "the register line went through the suspense")
        self.assertTrue(line.is_reconciled)
        self.assertTrue(line.move_id.checked)

    def test_cash_account_keeps_the_number_of_the_payment(self):
        self._set_payment_account(self.cash_journal, self.cash_account)
        payment = self._post_payment()

        self.assertTrue(payment.move_id.statement_line_id)
        self.assertEqual(payment.move_id.name, self.cash_journal.code + "CH000001")

    def test_cash_account_outbound_payment(self):
        self._set_payment_account(self.cash_journal, self.cash_account)
        payment = self._post_payment(payment_type="outbound", partner_type="supplier")

        line = payment.move_id.statement_line_id
        self.assertEqual(line.amount, -100.0, "money going out lowers the register")
        self.assertEqual(line.statement_id.balance_end, -100.0)

    def test_cash_account_payment_of_an_invoice(self):
        self._set_payment_account(self.cash_journal, self.cash_account)
        invoice = self._create_invoice_one_line(
            price_unit=100.0, partner_id=self.partner.id, post=True
        )
        wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create({"journal_id": self.cash_journal.id})
        )
        payment = wizard._create_payments()

        self.assertEqual(invoice.payment_state, "paid")
        line = payment.move_id.statement_line_id
        self.assertTrue(line, "the receipt did not reach the cash register")
        self.assertEqual(line.move_id, payment.move_id)
        self.assertTrue(line.is_reconciled)

    # -- the payment method takes a transit account: two entries -----------

    def test_transit_account_gets_its_own_entry(self):
        self._set_payment_account(self.cash_journal, self.transit_account)
        payment = self._post_payment()

        lines = payment.reconciled_statement_line_ids
        self.assertEqual(len(lines), 1, "the payment did not reach the cash register")
        self.assertNotEqual(
            lines.move_id, payment.move_id, "the two entries were merged"
        )
        self.assertIn(self.transit_account, lines.move_id.line_ids.account_id)
        self.assertIn(self.cash_account, lines.move_id.line_ids.account_id)
        self.assertEqual(payment.l10n_ro_statement_line_id, lines)
        self.assertEqual(payment.l10n_ro_statement_id, lines.statement_id)

    def test_transit_account_line_needs_no_reconciliation(self):
        self._set_payment_account(self.cash_journal, self.transit_account)
        payment = self._post_payment()

        line = payment.reconciled_statement_line_ids
        _liquidity, suspense, _other = line._seek_for_lines()
        self.assertFalse(suspense, "the register line went through the suspense")
        self.assertTrue(line.is_reconciled)
        transit = payment.move_id.line_ids.filtered(
            lambda aml: aml.account_id == self.transit_account
        )
        self.assertTrue(transit.reconciled, "the payment was left outstanding")

    # -- no account on the payment method: no entry, nothing to register ---

    def test_payment_without_entry_is_not_registered(self):
        payment = self._create_payment()
        payment.with_context(skip_readonly_check=True).outstanding_account_id = False
        payment.action_post()

        self.assertFalse(payment.move_id, "the payment should have no entry")
        self.assertFalse(self._statements(), "a register was opened for nothing")

    # -- journals which keep no register -----------------------------------

    def test_journal_without_the_cash_register_flag(self):
        self._set_payment_account(self.cash_journal, self.cash_account)
        self.cash_journal.l10n_ro_auto_statement = False
        payment = self._post_payment()

        self.assertFalse(payment.move_id.statement_line_id)
        self.assertFalse(self._statements())

    def test_bank_journal_is_never_a_cash_register(self):
        """A bank journal takes its statements from the bank, never from payments."""
        self.bank_journal.l10n_ro_auto_statement = True
        bank_line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.bank_journal.id,
                "date": "2024-01-15",
                "payment_ref": "transaction from the bank",
                "amount": 500.0,
            }
        )
        statement = self.env["account.bank.statement"].create(
            {
                "journal_id": self.bank_journal.id,
                "date": "2024-01-15",
                "line_ids": [Command.set(bank_line.ids)],
            }
        )
        payment = self._post_payment(journal_id=self.bank_journal.id)

        self.assertFalse(payment.move_id.statement_line_id)
        self.assertEqual(
            statement.line_ids, bank_line, "a line with no transaction behind it"
        )

    # -- the register itself ------------------------------------------------

    def test_one_register_per_day(self):
        self._set_payment_account(self.cash_journal, self.cash_account)
        first = self._post_payment()
        second = self._post_payment(amount=50.0)
        next_day = self._post_payment(date="2024-01-16")

        self.assertEqual(first.move_id.statement_id, second.move_id.statement_id)
        self.assertNotEqual(next_day.move_id.statement_id, first.move_id.statement_id)
        self.assertEqual(len(self._statements()), 2)
        self.assertEqual(first.move_id.statement_id.balance_end, 150.0)

    def test_the_register_takes_its_name_from_the_sequence(self):
        self._set_payment_account(self.cash_journal, self.cash_account)
        payment = self._post_payment()

        self.assertEqual(
            payment.move_id.statement_id.name, self.cash_journal.code + "RC000001"
        )

    def test_the_declared_balance_is_left_alone(self):
        """The module computes the register, it does not declare its balance."""
        self._set_payment_account(self.cash_journal, self.cash_account)
        payment = self._post_payment()
        statement = payment.move_id.statement_id
        statement.balance_end_real = 999.0

        self._post_payment(amount=50.0)

        self.assertEqual(statement.balance_end, 150.0)
        self.assertEqual(
            statement.balance_end_real, 999.0, "the declared balance was overwritten"
        )

    def test_changing_the_amount_reaches_the_register(self):
        """One entry for both, so the register follows the payment by itself."""
        self._set_payment_account(self.cash_journal, self.cash_account)
        payment = self._post_payment()
        line = payment.move_id.statement_line_id

        payment.action_draft()
        payment.amount = 250.0
        payment.action_post()

        self.assertEqual(
            payment.move_id.statement_line_id, line, "a second line was added"
        )
        self.assertEqual(line.amount, 250.0)
        self.assertEqual(line.statement_id.balance_end, 250.0)

    def test_cancelling_the_payment_cancels_the_register_line(self):
        self._set_payment_account(self.cash_journal, self.cash_account)
        payment = self._post_payment()
        line = payment.move_id.statement_line_id
        statement = line.statement_id

        payment.action_cancel()

        self.assertEqual(payment.state, "canceled")
        self.assertEqual(line.move_id.state, "cancel")
        self.assertEqual(statement.balance_end, 0.0, "the register still counts it")

    def test_the_payment_is_registered_only_once(self):
        self._set_payment_account(self.cash_journal, self.cash_account)
        payment = self._post_payment()

        payment._l10n_ro_add_to_statement()

        self.assertEqual(len(payment.move_id.statement_id.line_ids), 1)

    def test_reposting_the_payment_keeps_one_register_line(self):
        self._set_payment_account(self.cash_journal, self.cash_account)
        payment = self._post_payment()
        line = payment.move_id.statement_line_id
        name = payment.move_id.name

        payment.action_cancel()
        payment.action_draft()
        payment.action_post()

        self.assertEqual(payment.move_id.statement_line_id, line, "a second line")
        self.assertEqual(len(line.statement_id.line_ids), 1)
        self.assertEqual(line.move_id.state, "posted")
        self.assertEqual(line.statement_id.balance_end, 100.0)
        self.assertEqual(payment.move_id.name, name, "the number was burned")

    def test_reposting_on_another_day(self):
        self._set_payment_account(self.cash_journal, self.cash_account)
        payment = self._post_payment()
        line = payment.move_id.statement_line_id

        payment.action_cancel()
        payment.action_draft()
        payment.date = "2024-01-20"
        payment.action_post()

        self.assertEqual(line.date, fields.Date.to_date("2024-01-20"))
        self.assertEqual(
            line.statement_id.date,
            fields.Date.to_date("2024-01-20"),
            "the line stayed in the register of another day",
        )

    def test_reposting_on_another_day_leaves_the_first_register(self):
        self._set_payment_account(self.cash_journal, self.cash_account)
        stays = self._post_payment(amount=40.0)
        moved = self._post_payment(amount=60.0)
        first = stays.move_id.statement_id
        self.assertEqual(first.balance_end, 100.0)

        moved.action_cancel()
        moved.action_draft()
        moved.date = "2024-01-20"
        moved.action_post()

        self.assertEqual(first.date, fields.Date.to_date("2024-01-15"))
        self.assertEqual(first.line_ids, stays.move_id.statement_line_id)
        self.assertEqual(first.balance_end, 40.0)
        second = moved.move_id.statement_id
        self.assertNotEqual(second, first, "the line stayed in the first register")
        self.assertEqual(second.date, fields.Date.to_date("2024-01-20"))
        self.assertEqual(second.line_ids, moved.move_id.statement_line_id)
        self.assertEqual(
            moved.l10n_ro_statement_id,
            second,
            "the payment still points at the first register",
        )

    def test_the_register_line_is_not_rebuilt(self):
        """Writing on the line must not turn the entry into cash + suspense."""
        self._set_payment_account(self.cash_journal, self.cash_account)
        payment = self._post_payment()
        line = payment.move_id.statement_line_id

        line.write({"payment_ref": "changed by the accountant"})

        self.assertEqual(line.move_id, payment.move_id)
        accounts = line.move_id.line_ids.account_id
        self.assertIn(self.company_data["default_account_receivable"], accounts)
        self.assertNotIn(self.cash_journal.suspense_account_id, accounts)

    def test_a_numbered_cash_payment_cannot_be_deleted(self):
        self._set_payment_account(self.cash_journal, self.cash_account)
        payment = self._post_payment()

        with self.assertRaises(UserError):
            payment.unlink()
