# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from .common import TestPaymenttoStatement


@tagged("post_install", "-at_install")
class TestAccountJournal(TestPaymenttoStatement):
    """What a romanian cash journal gets when it is created."""

    def _create_journal(self, **vals):
        values = {
            "name": "Test cash",
            "code": "TST",
            "type": "cash",
            "company_id": self.env.company.id,
            **vals,
        }
        return self.env["account.journal"].create(
            {key: value for key, value in values.items() if value is not None}
        )

    def test_cash_journal_gets_its_sequences(self):
        journal = self._create_journal()

        self.assertTrue(journal.l10n_ro_journal_sequence_id)
        self.assertTrue(journal.l10n_ro_statement_sequence_id)
        self.assertTrue(journal.l10n_ro_cash_in_sequence_id)
        self.assertTrue(journal.l10n_ro_cash_out_sequence_id)
        self.assertTrue(journal.l10n_ro_customer_cash_in_sequence_id)

    def test_the_sequences_are_named_after_the_journal(self):
        journal = self._create_journal()

        self.assertEqual(journal.l10n_ro_statement_sequence_id.prefix, "TSTRC")
        self.assertEqual(journal.l10n_ro_customer_cash_in_sequence_id.prefix, "TSTCH")
        self.assertEqual(
            journal.l10n_ro_journal_sequence_id.company_id, self.env.company
        )

    def test_the_code_of_the_journal_is_the_one_odoo_settles_on(self):
        """Sequences are named after the code the journal really ends up with."""
        journal = self._create_journal(code=None)

        self.assertTrue(journal.code)
        self.assertEqual(
            journal.l10n_ro_statement_sequence_id.prefix, journal.code + "RC"
        )

    def test_the_cash_register_is_kept_by_default(self):
        self.assertTrue(self._create_journal().l10n_ro_auto_statement)

    def test_the_cash_register_can_be_refused(self):
        journal = self._create_journal(l10n_ro_auto_statement=False)

        self.assertFalse(journal.l10n_ro_auto_statement)
        self.assertTrue(journal.l10n_ro_statement_sequence_id, "sequences are set")

    def test_a_bank_journal_gets_nothing(self):
        journal = self._create_journal(type="bank", code="TSTB")

        self.assertFalse(journal.l10n_ro_auto_statement)
        self.assertFalse(journal.l10n_ro_statement_sequence_id)

    def test_a_journal_of_another_company_gets_nothing(self):
        other_company = self.setup_other_company()["company"]
        journal = self._create_journal(company_id=other_company.id)

        self.assertFalse(journal.l10n_ro_auto_statement)
        self.assertFalse(journal.l10n_ro_statement_sequence_id)
