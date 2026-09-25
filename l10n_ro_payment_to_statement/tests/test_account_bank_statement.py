# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, fields
from odoo.tests import tagged

from .common import TestPaymenttoStatement


@tagged("post_install", "-at_install")
class TestAccountBankStatement(TestPaymenttoStatement):
    """Names the statements take from the sequence of their journal."""

    def _create_statement(self, journal, **vals):
        return self.env["account.bank.statement"].create(
            {
                "date": "2024-01-15",
                "journal_id": journal.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "payment_ref": "/",
                            "amount": 100.0,
                            "journal_id": journal.id,
                        },
                    )
                ],
                **vals,
            }
        )

    def test_statement_sequence(self):
        statement = self._create_statement(self.cash_journal)
        self.assertEqual(statement.name, self.cash_journal.code + "RC000001")

    def test_without_statement_sequence(self):
        self.cash_journal.l10n_ro_statement_sequence_id = False
        statement = self._create_statement(self.cash_journal)
        self.assertEqual(statement.name, fields.Date.to_string(fields.Date.today()))

    def test_given_name_is_kept(self):
        statement = self._create_statement(self.cash_journal, name="Test")
        self.assertEqual(statement.name, "Test")

    def test_statement_made_out_of_its_lines(self):
        """The journal of a statement can come from its lines."""
        self.cash_journal.l10n_ro_auto_statement = False
        line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.cash_journal.id,
                "date": "2024-01-15",
                "payment_ref": "/",
                "amount": 100.0,
            }
        )
        statement = self.env["account.bank.statement"].create(
            {"line_ids": [Command.set(line.ids)]}
        )
        self.assertEqual(statement.journal_id, self.cash_journal)
        self.assertEqual(statement.name, self.cash_journal.code + "RC000001")

    def test_line_made_in_the_register_joins_the_day(self):
        """A cash in/out slip lands in the register of its day."""
        line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.cash_journal.id,
                "date": "2024-01-15",
                "payment_ref": "cash in",
                "amount": 100.0,
            }
        )
        self.assertEqual(line.statement_id.name, self.cash_journal.code + "RC000001")

    def test_statement_of_a_romanian_journal_from_another_company(self):
        """The naming follows the company of the journal, not the active one."""
        other_company = self.setup_other_company()["company"]
        statement = (
            self.env["account.bank.statement"]
            .with_context(allowed_company_ids=[other_company.id, self.env.company.id])
            .create(
                {
                    "date": "2024-01-15",
                    "journal_id": self.cash_journal.id,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "payment_ref": "/",
                                "amount": 100.0,
                                "journal_id": self.cash_journal.id,
                            },
                        )
                    ],
                }
            )
        )
        self.assertEqual(statement.env.company, other_company)
        self.assertEqual(statement.name, self.cash_journal.code + "RC000001")

    def test_statement_of_a_journal_which_is_not_romanian(self):
        """A journal of a company which is not romanian keeps the odoo name."""
        other = self.setup_other_company()
        statement = self._create_statement(other["default_journal_bank"])
        self.assertNotEqual(statement.name, fields.Date.to_string(fields.Date.today()))
        self.assertIn(other["default_journal_bank"].code, statement.name)
