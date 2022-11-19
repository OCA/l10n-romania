# Copyright (C) 2022 Terrabit
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
        self.bank = self.create_partner_bank("RO48RNCB0090000506460001")
        self.journal = self.create_journal("TBNK2MT940", self.bank, ron_curr)

        self.data = (
            "Referinta 221031S029321541, data valutei 31-10-2022, Decontare -"
            "Platitor  Test Partner BCR  RO24BREL0002002472400100  "
            "CODFISC 0-Beneficiar  NEXTERP ROMANIA SRL  RO48RNCB0090000506460001  "
            "CODFISC RO9731314-"
            "Detalii  /ROC/SERIA BTLAM NR 21036843 . . /RFB/31/20221028/20221031"
        )
        self.codewords = ["Referinta", "Platitor", "Beneficiar", "Detalii", "CODFISC"]
        self.transactions = [
            {
                "account_number": "RO24BREL0002002472400100",
                "partner_name": "Test Partner BCR",
                "amount": 1000.0,
                "payment_ref": "  /ROC/SERIA BTLAM NR 21036843 . . /RFB/31/20221028/20221031",
                "ref": "221031S029321541",
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
        parser = parser.with_context(type="mt940_ro_bcr")
        res = parser.get_subfields(self.data, self.codewords)
        espected_res = {
            "Referinta": [
                "221031S029321541,",
                "data",
                "valutei",
                "31",
                "10",
                "2022,",
                "Decontare",
                "",
            ],
            "Platitor": [
                "",
                "Test",
                "Partner",
                "BCR",
                "",
                "RO24BREL0002002472400100",
                "",
            ],
            "CODFISC": ["RO9731314"],
            "Beneficiar": [
                "",
                "NEXTERP",
                "ROMANIA",
                "SRL",
                "",
                "RO48RNCB0090000506460001",
                "",
            ],
            "Detalii": [
                "",
                "/ROC/SERIA",
                "BTLAM",
                "NR",
                "21036843",
                ".",
                ".",
                "/RFB/31/20221028/20221031",
            ],
        }

        self.assertTrue(res == espected_res)

    def test_handle_common_subfields(self):
        """Unit Test function handle_common_subfields()."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_bcr")
        subfields = parser.get_subfields(self.data, self.codewords)
        transaction = self.transactions[0]
        parser.handle_common_subfields(transaction, subfields)

    def test_statement_import(self):
        """Test correct creation of single statement BCR."""
        testfile = get_module_resource(
            "l10n_ro_account_bank_statement_import_mt940_bcr",
            "test_files",
            "test_file_bcr.STA",
        )
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_bcr")
        datafile = open(testfile, "rb").read()
        statements = parser.parse(datafile, header_lines=1)
        self._prepare_statement_lines(statements)
        self._load_statement(testfile, mt940_type="mt940_ro_bcr")
        bank_statements = self.get_statements(self.journal.id)
        statement = bank_statements[0]
        transact = self.transactions[0]
        line = statement.line_ids[0]
        self.assertTrue(line.account_number == transact["account_number"])
        self.assertTrue(line.partner_name == transact["partner_name"])
        self.assertTrue(line.amount == transact["amount"])
        self.assertTrue(line.date == fields.Date.from_string("2022-10-31"))
        self.assertTrue(line.payment_ref == transact["payment_ref"])
        self.assertTrue(line.ref == transact["ref"])
