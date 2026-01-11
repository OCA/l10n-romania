# Copyright 2017 Onestein (<http://www.onestein.eu>)
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields
from odoo.tests import tagged
from odoo.tools.misc import file_path

from .common import TestMT940BankStatementImport


@tagged("post_install", "-at_install")
class TestImport(TestMT940BankStatementImport):
    def setUp(self):
        super().setUp()
        eur_curr = self.env.ref("base.EUR")
        eur_curr.write({"active": True})
        self.bank = self.create_partner_bank("NL34RABO0142623393 EUR")
        self.journal = self.create_journal("TBNK2MT940", self.bank, eur_curr)

        self.data = "/BENM//NAME/Cost/REMI/Period 01-10-2013 t/m 31-12-2013/ISDT/20"
        self.codewords = [
            "RTRN",
            "BENM",
            "ORDP",
            "CSID",
            "BUSP",
            "MARF",
            "EREF",
            "PREF",
            "REMI",
            "ID",
            "PURP",
            "ULTB",
            "ULTD",
            "ISDT",
            "CREF",
            "IREF",
            "NAME",
            "ADDR",
            "ULTC",
            "EXCH",
            "CHGS",
        ]
        self.transactions = [
            {
                "account_number": "NL66RABO0160878799",
                "amount": 400.00,
                "payment_ref": "Test/money/paid/by/other/partner:",
                "ref": "NONREF",
            },
        ]

    def _prepare_statement_lines(self, statements):
        transact = self.transactions[0]
        for st_vals in statements[2]:
            for line_vals in st_vals["transactions"]:
                line_vals["amount"] = transact["amount"]
                line_vals["payment_ref"] = transact["payment_ref"]
                line_vals["account_number"] = transact["account_number"]
                line_vals["ref"] = transact["ref"]

    def test_get_subfields(self):
        """Unit Test function get_subfields()."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_general")
        res = parser.get_subfields(self.data, self.codewords)
        espected_res = {
            "BENM": [""],
            "NAME": ["Cost"],
            "REMI": ["Period", "01-10-2013", "t", "m", "31-12-2013"],
            "ISDT": ["20"],
        }
        self.assertTrue(res == espected_res)

    def test_handle_common_subfields(self):
        """Unit Test function handle_common_subfields()."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_general")
        subfields = parser.get_subfields(self.data, self.codewords)
        transaction = self.transactions[0]
        parser.handle_common_subfields(transaction, subfields)

    def test_statement_import(self):
        """Test correct creation of single statement ING."""

        testfile = file_path(
            "l10n_ro_account_bank_statement_import_mt940_base/test_files/test-rabo.swi"
        )
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_general")
        datafile = open(testfile, "rb").read()
        statements = parser.parse(datafile, header_lines=1)
        self._prepare_statement_lines(statements)
        self._load_statement(testfile)
        bank_statements = self.get_statements(self.journal.id)
        statement = bank_statements[0]
        transact = self.transactions[0]
        for line in statement.line_ids:
            self.assertTrue(line.account_number == transact["account_number"])
            self.assertTrue(line.amount == transact["amount"])
            self.assertTrue(line.date == fields.Date.from_string("2014-01-02"))
            self.assertTrue(line.payment_ref == transact["payment_ref"])
            self.assertTrue(line.ref == transact["ref"])

    def test_wrong_file_import(self):
        """Test wrong file import."""
        testfile = file_path(
            "l10n_ro_account_bank_statement_import_mt940_base/test_files/test-wrong-file.940",
        )
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_general")
        datafile = open(testfile, "rb").read()
        self.assertFalse(parser.parse(datafile, header_lines=1))

    def test_clean_codewords(self):
        """Unit Test function _clean_codewords()."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        data = "R T R N B E N M"
        codewords = ["RTRN", "BENM"]
        res = parser._clean_codewords(data, codewords)
        self.assertEqual(res, "RTRN BENM")

    def test_parse_amount(self):
        """Unit Test function parse_amount()."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        self.assertEqual(parser.parse_amount("C", "100,50"), 100.50)
        self.assertEqual(parser.parse_amount("D", "100,50"), -100.50)

    def test_handle_tag_25(self):
        """Unit Test function handle_tag_25()."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        result = {"account_number": None}
        parser.handle_tag_25("NL34.RABO.0142.623.393", result)
        self.assertEqual(result["account_number"], "NL34RABO0142623393")

    def test_handle_tag_20_and_28(self):
        """Unit Test function handle_tag_20() and handle_tag_28()."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        result = {"statement": {"name": None}}
        parser.handle_tag_20("STMT123", result)
        self.assertEqual(result["statement"]["name"], "STMT123")
        # handle_tag_28 should not change anything
        parser.handle_tag_28("000", result)
        self.assertEqual(result["statement"]["name"], "STMT123")
        parser.handle_tag_28C("000", result)
        self.assertEqual(result["statement"]["name"], "STMT123")

    def test_handle_tag_60F_and_62F(self):
        """Unit Test function handle_tag_60F() and handle_tag_62F()."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        result = {
            "currency": None,
            "account_number": "NL34RABO0142623393",
            "statement": {
                "name": None,
                "date": None,
                "balance_start": 0.0,
                "balance_end_real": 0.0,
            },
        }
        # C 221031 RON 1000,00
        parser.handle_tag_60F("C221031RON1000,00", result)
        self.assertEqual(result["currency"], "RON")
        self.assertEqual(result["statement"]["balance_start"], 1000.0)
        self.assertEqual(
            result["statement"]["date"].date(), fields.Date.from_string("2022-10-31")
        )

        # Test handle_tag_60M (calls 60F)
        result["currency"] = None
        parser.handle_tag_60M("C221031EUR2000,00", result)
        self.assertEqual(result["currency"], "EUR")

        # Test handle_tag_62F
        parser.handle_tag_62F("C221101EUR1500,00", result)
        self.assertEqual(result["statement"]["balance_end_real"], 1500.0)
        self.assertEqual(
            result["statement"]["date"].date(), fields.Date.from_string("2022-11-01")
        )
        self.assertTrue(result["statement"]["name"].startswith("NL34RABO0142623393"))

        # Test handle_tag_62M (calls 62F)
        parser.handle_tag_62M("C221102EUR1200,00", result)
        self.assertEqual(result["statement"]["balance_end_real"], 1200.0)

    def test_handle_tag_64_65(self):
        """Test handle_tag_64 and 65 (ignored tags)."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        result = {}
        self.assertEqual(parser.handle_tag_64("data", result), result)
        self.assertEqual(parser.handle_tag_65("data", result), result)

    def test_is_mt940_statement_error(self):
        """Test is_mt940_statement raises ValueError."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        with self.assertRaises(ValueError):
            parser.is_mt940_statement("Invalid Line")

    def test_get_counterpart(self):
        """Unit Test function get_counterpart()."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        transaction = {}
        # subfield [account, partner, partner_fallback]
        parser.get_counterpart(transaction, ["ACC123", "PARTNER1", "PARTNER2"])
        self.assertEqual(transaction["account_number"], "ACC123")
        self.assertEqual(transaction["partner_name"], "PARTNER1")

        transaction = {}
        parser.get_counterpart(transaction, ["ACC456", "", "PARTNER2"])
        self.assertEqual(transaction["account_number"], "ACC456")
        self.assertEqual(transaction["partner_name"], "PARTNER2")

    def test_pre_process_data_variants(self):
        """Test pre_process_data with different formats."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        # Case with {4:
        # Each :20: in the data (if data starts with header_regex) creates a match
        data = ":940:\n:20:STMT1\n:20:STMT2"
        res = parser.pre_process_data(data)
        self.assertEqual(len(res), 2)

        # Case with default fallback to tag_re
        data = "{4:\n:20:STMT3\n}{4:\n:20:STMT4\n}"
        res = parser.pre_process_data(data)
        self.assertEqual(len(res), 2)
