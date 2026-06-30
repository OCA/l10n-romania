# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

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
        self.bank = self.create_partner_bank("RO49BRMA1030025122260001")
        self.journal = self.create_journal("TBNK2MT940EXIM", self.bank, ron_curr)

    def test_statement_import(self):
        """Test correct creation of single statement EXIM."""
        testfile = file_path(
            "l10n_ro_account_bank_statement_import_mt940_exim/test_files/"
            "test_file_exim.mt940",
        )
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_exim")
        datafile = open(testfile, "rb").read()
        currency, account_number, statements = parser.parse(datafile, header_lines=1)

        self.assertEqual(currency, "RON")
        self.assertEqual(account_number, "RO49BRMA1030025122260001")
        self.assertEqual(len(statements), 1)
        statement = statements[0]
        self.assertEqual(statement["balance_start"], 72759.07)
        self.assertEqual(statement["balance_end_real"], 52950.49)
        self.assertEqual(statement["name"], "26090")
        # self.assertEqual(statement["date"], fields.Date.from_string("2026-03-31"))
        self.assertEqual(len(statement["transactions"]), 4)

        transaction1 = statement["transactions"][0]
        self.assertEqual(transaction1["amount"], -20505.68)
        self.assertEqual(transaction1["ref"], "00000001")
        self.assertIn("Rambursare dobanda", transaction1["payment_ref"])
        self.assertNotIn("Counterpart:", transaction1["payment_ref"])
        # self.assertEqual(transaction1["partner_name"], "EXEMPLU SRL")

        transaction2 = statement["transactions"][1]
        self.assertEqual(transaction2["amount"], -3.00)
        self.assertEqual(transaction2["ref"], "00000002")
        self.assertIn(
            "Incasare comision administrare cont curent", transaction2["payment_ref"]
        )
        self.assertNotIn("Counterpart:", transaction2["payment_ref"])
        # self.assertEqual(transaction2["partner_name"], "EXEMPLU SRL")

        transaction3 = statement["transactions"][2]
        self.assertEqual(transaction3["amount"], 300.00)
        self.assertEqual(transaction3["ref"], "00000003")
        self.assertIn("Incasare OP", transaction3["payment_ref"])
        self.assertNotIn("Counterpart:", transaction3["payment_ref"])
        self.assertEqual(transaction3["partner_name"], "NEXTERP ROMANIA SRL")

        transaction4 = statement["transactions"][3]
        self.assertEqual(transaction4["amount"], 400.10)
        self.assertEqual(transaction4["ref"], "00000004")
        self.assertIn("Incasare OP", transaction4["payment_ref"])
        self.assertNotIn("Counterpart:", transaction4["payment_ref"])
        self.assertEqual(transaction4["partner_name"], "SMAROVIAL SOFTWARE S R L")

    def test_full_import(self):
        """Test the full import flow via account.statement.import."""
        testfile = file_path(
            "l10n_ro_account_bank_statement_import_mt940_exim/test_files/"
            "test_file_exim.mt940",
        )
        self._load_statement(testfile, mt940_type="mt940_ro_exim")
        bank_statements = self.get_statements(self.journal.id)
        self.assertTrue(bank_statements)
        statement = bank_statements[0]
        self.assertEqual(len(statement.line_ids), 4)
