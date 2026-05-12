# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields
from odoo.tests import tagged
from odoo.tools.misc import file_path

from odoo.addons.l10n_ro_account_bank_statement_import_mt940_base.tests.common import (
    TestMT940BankStatementImport,
)


@tagged("post_install", "-at_install")
class TestImport(TestMT940BankStatementImport):
    def setUp(self):
        super().setUp()
        ron_curr = self.env.ref("base.RON")
        ron_curr.write({"active": True})
        self.bank = self.create_partner_bank("RO49BTRLRONABCD0A1234567890")
        self.journal = self.create_journal("TBNK2MT940BT", self.bank, ron_curr)

    def test_statement_import(self):
        """Test correct creation of single statement BT."""
        testfile = file_path(
            "l10n_ro_account_bank_statement_import_mt940_bt/test_files/test_file_bt.txt",
        )
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_bt")
        datafile = open(testfile, "rb").read()
        currency, account_number, statements = parser.parse(datafile, header_lines=1)

        self.assertEqual(currency, "RON")
        self.assertEqual(account_number, "RO49BTRLRONABCD0A1234567890")
        self.assertEqual(len(statements), 1)
        statement = statements[0]
        self.assertEqual(statement["balance_start"], 11172.79)
        self.assertEqual(statement["balance_end_real"], 7774.26)
        self.assertEqual(statement["date"], fields.Date.from_string("2026-03-28"))
        self.assertEqual(len(statement["transactions"]), 4)

        transactions = statement["transactions"]
        self.assertEqual(transactions[0]["amount"], -159.42)
        self.assertEqual(transactions[0]["ref"], "000TESTPOS00001A")
        self.assertIn("Plata la POS non-BT", transactions[0]["payment_ref"])

        self.assertEqual(transactions[1]["amount"], -2000.0)
        self.assertEqual(transactions[1]["ref"], "000TESTPOS00002B")
        self.assertEqual(transactions[2]["amount"], -1207.43)
        self.assertEqual(transactions[3]["amount"], -31.68)

        # The trailing :86: after :62F:/:64: ("Total tranzactii card...")
        # must not overwrite the last transaction.
        self.assertNotIn("Total tranzactii", transactions[-1]["payment_ref"])

    def test_full_import(self):
        """Test the full import flow via account.statement.import."""
        testfile = file_path(
            "l10n_ro_account_bank_statement_import_mt940_bt/test_files/test_file_bt.txt",
        )
        self._load_statement(testfile, mt940_type="mt940_ro_bt")
        bank_statements = self.get_statements(self.journal.id)
        self.assertTrue(bank_statements)
        statement = bank_statements[0]
        self.assertEqual(len(statement.line_ids), 4)
