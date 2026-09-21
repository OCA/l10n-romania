# Copyright (C) 2023 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from .common import TestPaymenttoStatement


@tagged("post_install", "-at_install")
class TestAccountMove(TestPaymenttoStatement):
    """Entries take their number from the sequence set on their journal."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.invoice_sequence = cls.env["ir.sequence"].create(
            {
                "name": "Invoices",
                "code": "INV",
                "implementation": "no_gap",
                "prefix": "FCT/",
                "padding": 5,
                "company_id": cls.env.company.id,
            }
        )
        cls.sale_journal = cls.env["account.journal"].create(
            {
                "name": "Test sale",
                "code": "TSTS",
                "type": "sale",
                "l10n_ro_journal_sequence_id": cls.invoice_sequence.id,
                "company_id": cls.env.company.id,
            }
        )

    def _create_sale_invoice(self):
        return self._create_invoice_one_line(
            price_unit=10.0,
            partner_id=self.partner.id,
            journal_id=self.sale_journal.id,
            post=True,
        )

    def test_invoice_number(self):
        self.assertEqual(self._create_sale_invoice().name, "FCT/00001")
        self.assertEqual(self._create_sale_invoice().name, "FCT/00002")

    def test_the_number_is_taken_when_the_entry_is_posted(self):
        invoice = self._create_invoice_one_line(
            price_unit=10.0,
            partner_id=self.partner.id,
            journal_id=self.sale_journal.id,
        )
        self.assertFalse(invoice.name, "a draft took a number")

        invoice.action_post()

        self.assertEqual(invoice.name, "FCT/00001")

    def test_a_discarded_draft_leaves_no_gap(self):
        self.assertEqual(self._create_sale_invoice().name, "FCT/00001")
        discarded = self._create_invoice_one_line(
            price_unit=10.0,
            partner_id=self.partner.id,
            journal_id=self.sale_journal.id,
        )
        discarded.unlink()

        self.assertEqual(self._create_sale_invoice().name, "FCT/00002")

    def test_a_miscellaneous_journal_takes_its_sequence_too(self):
        """The sequence of a journal is not only for invoices."""
        journal = self.env["account.journal"].create(
            {
                "name": "Test misc",
                "code": "TSTM",
                "type": "general",
                "l10n_ro_journal_sequence_id": self.invoice_sequence.copy(
                    {"code": "MISC", "prefix": "NC/"}
                ).id,
                "company_id": self.env.company.id,
            }
        )
        account = self.company_data["default_account_revenue"]
        entry = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": journal.id,
                "date": "2024-01-15",
                "line_ids": [
                    (0, 0, {"name": "d", "account_id": account.id, "debit": 10.0}),
                    (0, 0, {"name": "c", "account_id": account.id, "credit": 10.0}),
                ],
            }
        )
        entry.action_post()

        self.assertEqual(entry.name, "NC/00001")
