# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields
from odoo.tests import tagged

from .common import TestPaymenttoStatement


@tagged("post_install", "-at_install")
class TestAccountBankStatement(TestPaymenttoStatement):
    def setUp(self):
        super(TestAccountBankStatement, self).setUp()

    def test_create_bank_statement(self):
        # Create statement with l10n_ro_statement_sequence_id in cash journal
        bnk1 = self.env["account.bank.statement"].create(
            {
                "date": "2022-12-01",
                "journal_id": self.company_data["default_journal_cash"].id,
                "company_id": self.env.company.id,
                "line_ids": [(0, 0, {"payment_ref": "/", "amount": 100.0})],
            }
        )
        self.assertEqual(bnk1.name, "CSH1RC-000001")

        # Create statement without l10n_ro_statement_sequence_id in cash journal
        journal = self.company_data["default_journal_cash"]
        journal.l10n_ro_statement_sequence_id = False
        bnk2 = self.env["account.bank.statement"].create(
            {
                "date": "2022-12-01",
                "journal_id": journal.id,
                "company_id": self.env.company.id,
                "line_ids": [(0, 0, {"payment_ref": "/", "amount": 100.0})],
            }
        )
        self.assertEqual(bnk2.name, fields.Date.to_string(fields.Date.today()))

    def test_name_get(self):
        bnk3 = self.env["account.bank.statement"].create(
            {
                "name": "/",
                "date": "2022-12-01",
                "journal_id": self.company_data["default_journal_bank"].id,
                "company_id": self.env.company.id,
                "line_ids": [(0, 0, {"payment_ref": "/", "amount": 100.0})],
            }
        )
        self.assertEqual(bnk3.name, fields.Date.to_string(fields.Date.today()))

    def test_for_cash_with_sequence(self):
        journal = self.env["account.journal"].create(
            {"name": "Test cash", "type": "cash", "company_id": self.env.company.id}
        )
        bnk4 = self.env["account.bank.statement"].create(
            {
                "name": "Test",
                "date": "2022-12-01",
                "journal_id": journal.id,
                "company_id": self.env.company.id,
                "line_ids": [(0, 0, {"payment_ref": "/", "amount": 100.0})],
            }
        )
        self.assertEqual(bnk4.name, "Test")
