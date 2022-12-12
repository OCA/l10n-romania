# Copyright (C) 2016 Forest and Biomass Romania
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields
from odoo.modules.module import get_module_resource

from odoo.addons.l10n_ro_account_bank_statement_import_mt940_base.tests.common import (
    TestMT940BankStatementImport,
)


class TestImport(TestMT940BankStatementImport):
    def setUp(self):
        super(TestImport, self).setUp()
        ron_curr = self.env.ref("base.RON")
        self.bank = self.create_partner_bank("RO40RZBR0000060001111111")
        self.journal = self.create_journal("TBNK3MT940", self.bank, ron_curr)

        self.data = """000^20F.2059628^24Ref.Doc 2268/OPMC^30RAIFFEIS
EN BANK S.A.^31RO05RZBR0000060003144073^32QUEHENBE
RGER LOGISTICS ROU"""
        self.codewords = [
            "20",
            "21",
            "22",
            "23",
            "24",
            "25",
            "26",
            "27",
            "30",
            "31",
            "32",
            "33",
            "61",
            "62",
        ]
        self.transactions = [
            {
                "account_number": "RO05RZBR0000060003144073",
                "partner_name": "QUEHENBERGER LOGISTICS ROU",
                "amount": 1179.87,
                "payment_ref": "/F.2059628Ref.Doc 2268/OPMC",
                "ref": "11808959",
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
        parser = parser.with_context(type="mt940_ro_rffsn")
        res = parser.get_subfields(self.data, self.codewords)
        espected_res = {
            "20": ["F.2059628"],
            "30": ["RAIFFEISEN BANK S.A."],
            "31": ["RO05RZBR0000060003144073"],
            "32": ["QUEHENBERGER LOGISTICS ROU"],
            "24": ["Ref.Doc 2268/OPMC"],
        }

        self.assertTrue(res == espected_res)

    def test_handle_common_subfields(self):
        """Unit Test function handle_common_subfields()."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_rffsn")
        subfields = parser.get_subfields(self.data, self.codewords)
        transaction = self.transactions[0]
        parser.handle_common_subfields(transaction, subfields)

    def test_statement_import(self):
        """Test correct creation of single statement BCR."""
        testfile = get_module_resource(
            "l10n_ro_account_bank_statement_import_mt940_rffsn",
            "test_files",
            "test_rffsn_940.txt",
        )
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_rffsn")
        datafile = open(testfile, "rb").read()
        statements = parser.parse(datafile, header_lines=1)
        self._prepare_statement_lines(statements)
        self._load_statement(testfile, mt940_type="mt940_ro_rffsn")
        bank_statements = self.get_statements(self.journal.id)
        statement = bank_statements[0]
        transact = self.transactions[0]
        line = statement.line_ids[0]
        self.assertTrue(line.account_number == transact["account_number"])
        self.assertTrue(line.partner_name == transact["partner_name"])
        self.assertAlmostEqual(line.amount, transact["amount"], 3)
        self.assertTrue(line.date == fields.Date.from_string("2012-06-18"))
        self.assertTrue(line.payment_ref == transact["payment_ref"])
        self.assertTrue(line.ref == transact["ref"])
