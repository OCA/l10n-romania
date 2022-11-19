# Copyright 2017 Onestein (<http://www.onestein.eu>)
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields
from odoo.modules.module import get_module_resource

from .common import TestMT940BankStatementImport


class TestImport(TestMT940BankStatementImport):
    def setUp(self):
        super(TestImport, self).setUp()
        eur_curr = self.env.ref("base.EUR")
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

        testfile = get_module_resource(
            "l10n_ro_account_bank_statement_import_mt940_base",
            "test_files",
            "test-rabo.swi",
        )
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_general")
        datafile = open(testfile, "rb").read()
        statements = parser.parse(datafile, header_lines=1)
        self._prepare_statement_lines(statements)
        self._load_statement(testfile)
        bank_statements = self.get_statements(self.journal.id)
        statement = bank_statements[1]
        transact = self.transactions[0]
        for line in statement.line_ids:
            self.assertTrue(line.account_number == transact["account_number"])
            self.assertTrue(line.amount == transact["amount"])
            self.assertTrue(line.date == fields.Date.from_string("2014-01-02"))
            self.assertTrue(line.payment_ref == transact["payment_ref"])
            self.assertTrue(line.ref == transact["ref"])

    def test_wrong_file_import(self):
        """Test wrong file import."""
        testfile = get_module_resource(
            "l10n_ro_account_bank_statement_import_mt940_base",
            "test_files",
            "test-wrong-file.940",
        )
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_general")
        datafile = open(testfile, "rb").read()
        with self.assertRaises(ValueError):
            parser.parse(datafile, header_lines=1)
