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
        self.assertEqual(statement["name"], "00060/00001")
        # self.assertEqual(statement["date"], fields.Date.from_string("2026-03-28"))
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

    def test_statement_import_bt940(self):
        """Test correct parsing of test_bt_940.txt (15 transactions, BT format)."""
        testfile = file_path(
            "l10n_ro_account_bank_statement_import_mt940_bt/test_files/test_bt_940.txt",
        )
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_bt")
        datafile = open(testfile, "rb").read()
        currency, account_number, statements = parser.parse(datafile, header_lines=1)

        self.assertEqual(currency, "RON")
        self.assertEqual(account_number, "RO49BTRLRONABCD0A1234567890")
        self.assertEqual(len(statements), 1)
        statement = statements[0]
        self.assertEqual(statement["name"], "00004/00001")
        self.assertEqual(statement["balance_start"], 38634.33)
        self.assertEqual(statement["balance_end_real"], 70800.97)
        # self.assertEqual(statement["date"], fields.Date.from_string("2025-01-09"))
        self.assertEqual(len(statement["transactions"]), 15)

        transactions = statement["transactions"]

        # ATM cash deposits (Credit)
        self.assertEqual(transactions[0]["amount"], 10600.00)
        self.assertEqual(transactions[0]["ref"], "029ATCD25008AGZB")
        self.assertIn("Depunere numerar ATM", transactions[0]["payment_ref"])

        self.assertEqual(transactions[1]["amount"], 6300.00)
        self.assertEqual(transactions[1]["ref"], "029ATCD25008AIIS")

        # POS batch settlements (Credit)
        self.assertEqual(transactions[2]["amount"], 965.00)
        self.assertEqual(transactions[3]["amount"], 9422.99)
        self.assertEqual(transactions[4]["amount"], 979.00)

        # Merchant commission charges (Debit)
        self.assertEqual(transactions[5]["amount"], -64.79)
        self.assertEqual(transactions[6]["amount"], -29.67)

        # OP intra-bank payment — partner and counterpart IBAN extracted from tag 86
        self.assertEqual(transactions[7]["amount"], -4115.00)
        self.assertEqual(transactions[7]["ref"], "029ZEXA2500901JT")
        self.assertIn("Plata OP intra", transactions[7]["payment_ref"])
        self.assertEqual(
            transactions[7].get("partner_name"), "WORK UP CONSULTING MARKETING SRL"
        )
        self.assertEqual(
            transactions[7].get("account_number"), "RO58BTRLRONCRT0259735901"
        )

        # Incoming OP — partner (with CIF), counterpart IBAN extracted from tag 86
        self.assertEqual(transactions[8]["amount"], 4821.00)
        self.assertEqual(transactions[8]["ref"], "139ZEXA2500902BX")
        self.assertEqual(transactions[8].get("partner_name"), "MAROCO AMBIENT SRL")
        self.assertEqual(
            transactions[8].get("account_number"), "RO60BTRLRONCRT0447604301"
        )

        # Inter-bank OP payment — partner and counterpart IBAN extracted from tag 86
        self.assertEqual(transactions[9]["amount"], -187.53)
        self.assertEqual(transactions[9]["ref"], "029ZEXA2500901JY")
        self.assertEqual(transactions[9].get("partner_name"), "COMPANIA DE APA OLT")
        self.assertEqual(
            transactions[9].get("account_number"), "RO33BRDE290SV14995572900"
        )

        # OP commission + merchant commission (no partner, no IBAN)
        self.assertEqual(transactions[10]["amount"], -0.51)
        self.assertEqual(transactions[11]["amount"], -5.87)

        # Large debit instrument — counterpart IBAN extracted, no partner pattern
        self.assertEqual(transactions[12]["amount"], -44667.98)
        self.assertEqual(transactions[12]["ref"], "029PIDB250090001")
        self.assertEqual(
            transactions[12].get("account_number"), "RO37BTRLRONCRT0442612901"
        )

        # Internal transfer (Alimentare cont) — partner extracted, no counterpart IBAN
        self.assertEqual(transactions[13]["amount"], 47000.00)
        self.assertEqual(transactions[13]["ref"], "029ECIT250094005")
        self.assertIn("Alimentare cont", transactions[13]["payment_ref"])
        self.assertEqual(transactions[13].get("partner_name"), "Societatea ABC SRL")

        # Last incoming OP — same counterpart as transactions[7], CIF present
        self.assertEqual(transactions[14]["amount"], 1150.00)
        self.assertEqual(transactions[14]["ref"], "029ZEXA2500900TI")
        self.assertEqual(
            transactions[14].get("partner_name"), "WORK UP CONSULTING MARKETING SRL"
        )
        self.assertEqual(
            transactions[14].get("account_number"), "RO58BTRLRONCRT0259735901"
        )

    def test_full_import_bt940(self):
        """Test the full import flow via
        account.statement.import for test_bt_940.txt."""
        testfile = file_path(
            "l10n_ro_account_bank_statement_import_mt940_bt/test_files/test_bt_940.txt",
        )
        self._load_statement(testfile, mt940_type="mt940_ro_bt")
        bank_statements = self.get_statements(self.journal.id)
        self.assertTrue(bank_statements)
        statement = bank_statements[0]
        self.assertEqual(len(statement.line_ids), 15)
