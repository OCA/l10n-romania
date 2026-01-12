# Copyright (C) 2016 Forest and Biomass Romania
# Copyright (C) 2022 Terrabit
# Copyright (C) 2022 NextERP Romania
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
        self.bank = self.create_partner_bank("RO19INGB0000999904621843")
        self.bank.bank_id.bic = "INGBROBU"
        self.journal = self.create_journal("TBNK2MT940", self.bank, ron_curr)

        self.data = """035~20AMT RCD RON 1000,00        ~21                           ~
22                           ~32NEXTERP ROMANIA SRL    ~33RO2
5INGB0014000031948911   ~23                           ~24
                   ~25CVF 2020/0060 . 344944869  ~26
              ~27                           ~28
         ~29                           ~60     ~61              ~"""
        self.codewords = [
            "20",
            "21",
            "22",
            "23",
            "25",
            "26",
            "27",
            "28",
            "29",
            "31",
            "32",
            "33",
            "60",
            "61",
            "110",
            "NAME ACCOUNT OWNER",
            "IBAN NO",
        ]

        self.transactions = [
            {
                "account_number": "RO25INGB0014000031948911",
                "partner_name": "NEXTERP ROMANIA SRL",
                "amount": 1000.0,
                "payment_ref": "/24CVF 2020/0060 . 344944869NEXTERP ROMANIA SRL",
                "ref": "RE20200211-7523",
            },
        ]

    def _prepare_statement_lines(self, statements):
        transact = self.transactions[0]
        for st_vals in statements[2]:
            for line_vals in st_vals["transactions"]:
                line_vals["amount"] = transact["amount"]
                line_vals["payment_ref"] = transact["payment_ref"]
                line_vals["account_number"] = transact["account_number"]
                line_vals["partner_name"] = transact["partner_name"]
                line_vals["ref"] = transact["ref"]

    def test_get_subfields(self):
        """Unit Test function get_subfields()."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_ing")
        res = parser.get_subfields(self.data, self.codewords)
        espected_res = {
            "20": ["AMT RCD RON 1000,00"],
            "21": [""],
            "22": [""],
            "32": ["NEXTERP ROMANIA SRL"],
            "33": ["RO25INGB0014000031948911"],
            "23": ["", "24"],
            "25": ["CVF 2020/0060 . 344944869"],
            "26": [""],
            "27": [""],
            "28": [""],
            "29": [""],
            "60": [""],
            "61": ["", ""],
        }
        self.assertTrue(res == espected_res)

    def test_handle_common_subfields(self):
        """Unit Test function handle_common_subfields()."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_ing")
        subfields = parser.get_subfields(self.data, self.codewords)
        transaction = self.transactions[0]
        parser.handle_common_subfields(transaction, subfields)

    def test_statement_import(self):
        """Test correct creation of single statement BCR."""
        testfile = file_path(
            "l10n_ro_account_bank_statement_import_mt940_ing/test_files/test_ing_940.txt",
        )
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_ing")
        datafile = open(testfile, "rb").read()
        statements = parser.parse(datafile, header_lines=1)
        self._prepare_statement_lines(statements)
        self._load_statement(testfile, mt940_type="mt940_ro_ing")
        bank_statements = self.get_statements(self.journal.id)
        statement = bank_statements[0]
        transact = self.transactions[0]
        line = statement.line_ids[0]

        self.assertTrue(line.account_number == transact["account_number"])
        self.assertTrue(line.partner_name == transact["partner_name"])
        self.assertTrue(line.amount == transact["amount"])
        self.assertTrue(line.date == fields.Date.from_string("2020-02-11"))
        self.assertTrue(line.payment_ref == transact["payment_ref"])
        self.assertTrue(line.ref == transact["ref"])

    def test_statement_unstructured_import(self):
        """Test correct creation of single unstructured statement BCR."""
        testfile = file_path(
            "l10n_ro_account_bank_statement_import_mt940_ing/test_files/test_ing_940n.txt",
        )
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_ing", journal_id=self.journal.id)
        datafile = open(testfile, "rb").read()
        statements = parser.parse(datafile, header_lines=1)
        self._prepare_statement_lines(statements)
        self._load_statement(testfile, mt940_type="mt940_ro_ing")
        bank_statements = self.get_statements(self.journal.id)
        statement = bank_statements[0]
        transact = self.transactions[0]
        line = statement.line_ids[0]

        self.assertTrue(line.account_number == transact["account_number"])
        self.assertTrue(line.partner_name == transact["partner_name"])
        self.assertTrue(line.amount == transact["amount"])
        self.assertTrue(line.date == fields.Date.from_string("2020-02-11"))
        self.assertTrue(line.payment_ref == transact["payment_ref"])
        self.assertTrue(line.ref == transact["ref"])

    def test_is_ing(self):
        """Test _is_ing function."""
        wizard = self.env["account.statement.import"].with_context(
            journal_id=self.journal.id
        )
        self.assertTrue(wizard._is_ing())

        wizard = self.env["account.statement.import"].with_context(mt940_ro_ing=True)
        self.assertTrue(wizard._is_ing())

    def test_parse_file_no_bank(self):
        """Test _parse_file when no matching bank account is found."""
        testfile = file_path(
            "l10n_ro_account_bank_statement_import_mt940_ing/test_files/test_ing_940.txt",
        )
        datafile = open(testfile, "rb").read()
        # Create a wizard without the bank account in company bank_ids
        self.bank.unlink()
        wizard = self.env["account.statement.import"].with_context(mt940_ro_ing=True)
        res = wizard._parse_file(datafile)
        self.assertEqual(res[1], "RO19INGB0000999904621843")

    def test_handle_tag_61_nonref(self):
        """Test handle_tag_61 with NONREF reference."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_ing")
        result = {"statement": {"transactions": []}}
        data = "200211CN1000,00NTRFNONREF//INGID123-TRANSCODE456"
        parser.handle_tag_61(data, result)
        transaction = result["statement"]["transactions"][0]
        self.assertEqual(transaction["ref"], "INGID123-TRANSCODE456")

    def test_handle_common_subfields_partner_search(self):
        """Test handle_common_subfields search partner by name."""
        partner = self.env["res.partner"].create({"name": "TEST PARTNER SRL"})
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_ing")
        transaction = {"amount": 100.0}
        subfields = {"32": ["TEST PARTNER SRL"]}
        parser.handle_common_subfields(transaction, subfields)
        self.assertEqual(transaction.get("partner_id"), partner.id)

    def test_handle_common_subfields_31_cleaning(self):
        """Test handle_common_subfields cleaning spaces in 31."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_ing")
        transaction = {"amount": 100.0}
        # In handle_common_subfields:
        # tag "31" is cleaned of spaces and put in counterpart_fields[0]
        # In get_counterpart:
        # counterpart_fields[0] is put in partner_name
        # counterpart_fields[1] is put in account_number
        subfields = {
            "31": ["RO25 INGB 0014 0000 3194 8911"],
            "32": ["PARTNER NAME"],
        }
        parser.handle_common_subfields(transaction, subfields)
        # partner_name will be the cleaned 31
        self.assertEqual(transaction.get("partner_name"), "RO25INGB0014000031948911")

    def test_handle_common_subfields_100_vat_search(self):
        """Test handle_common_subfields_100 search partner by VAT."""
        # Create partner with unique name and VAT
        unique_vat = "99999999"
        unique_name = "UNIQUE VAT PARTNER"
        partner = self.env["res.partner"].create(
            {
                "name": unique_name,
                "vat": "RO" + unique_vat,
                "l10n_ro_vat_number": unique_vat,
            }
        )
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_ing", journal_id=self.journal.id)
        transaction = {}
        # INCASARE UNIQUE VAT PARTNER 99999999 RO25INGB0014000031948911
        subfields = {
            "110": [
                "INCASARE "
                + unique_name
                + " "
                + unique_vat
                + " RO25INGB0014000031948911"
            ]
        }
        parser.handle_common_subfields_100(transaction, subfields)
        self.assertEqual(transaction.get("partner_id"), partner.id)
        self.assertEqual(transaction.get("partner_name"), unique_name)
        self.assertEqual(transaction.get("account_number"), "RO25INGB0014000031948911")

    def test_handle_tag_28_and_62F(self):
        """Test handle_tag_28 and handle_tag_62F for statement name."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_ing")
        acc_number = "RO19INGB0000999904621843"
        result = {
            "statement": {"name": None, "transactions": [], "date": None},
            "account_number": acc_number,
        }
        # Test handle_tag_28
        parser.handle_tag_28("00015/00001", result)
        self.assertEqual(result["statement"]["name"], "00015/00001")

        # Set name to account number to trigger the specific logic in 62F
        result["statement"]["name"] = acc_number
        # Test handle_tag_62F
        # C200211RON2000,00 -> date 200211 (2020-02-11), balance 2000.00
        parser.handle_tag_62F("C200211RON2000,00", result)
        self.assertEqual(result["statement"]["name"], acc_number + " - 2020-02-11")
        self.assertEqual(result["statement"]["balance_end_real"], 2000.0)

    def test_get_counterpart_variants(self):
        """Test get_counterpart with different subfield lengths."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_ing")

        # Length 1
        transaction = {}
        parser.get_counterpart(transaction, ["PARTNER NAME"])
        self.assertEqual(transaction.get("partner_name"), "PARTNER NAME")

        # Length 2
        transaction = {}
        parser.get_counterpart(transaction, ["PARTNER NAME", "ACC123"])
        self.assertEqual(transaction.get("account_number"), "ACC123")

        # Length 3, account_number already set
        transaction = {"account_number": "ACC123"}
        parser.get_counterpart(transaction, ["PARTNER NAME", "ACC456", "UNUSED"])
        self.assertEqual(
            transaction.get("account_number"), "ACC456"
        )  # Index 1 is not empty, so it updates

        # Length 3, account_number not set, uses index 2
        transaction = {}
        parser.get_counterpart(transaction, ["PARTNER NAME", "", "ACC789"])
        self.assertEqual(transaction.get("account_number"), "ACC789")
