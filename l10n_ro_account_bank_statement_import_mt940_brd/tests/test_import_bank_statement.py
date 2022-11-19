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
        self.bank = self.create_partner_bank("RO56BRDE360SV52474653600")
        self.journal = self.create_journal("TBNK2MT940", self.bank, ron_curr)

        self.data = """000+20Plata           +30302410000+31RO89RZBR0000060003480121
+32NEXTERP ROMANIA SRL+33/
+23PLATA FACT 4603309"""
        self.codewords = [
            "20",
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
                "account_number": "RO89RZBR0000060003480121",
                "partner_name": "NEXTERP ROMANIA SRL",
                "amount": 1000.0,
                "payment_ref": "/PLATA FACT 4603309",
                "ref": "OPH478PLATA",
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
        parser = parser.with_context(type="mt940_ro_brd")
        res = parser.get_subfields(self.data, self.codewords)
        espected_res = {
            "20": ["Plata           "],
            "30": ["302410000"],
            "31": ["RO89RZBR0000060003480121"],
            "32": ["NEXTERP ROMANIA SRL"],
            "33": ["/"],
            "23": ["PLATA FACT 4603309"],
        }

        self.assertTrue(res == espected_res)

    def test_handle_common_subfields(self):
        """Unit Test function handle_common_subfields()."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_brd")
        subfields = parser.get_subfields(self.data, self.codewords)
        transaction = self.transactions[0]
        parser.handle_common_subfields(transaction, subfields)

    def test_statement_import(self):
        """Test correct creation of single statement BCR."""
        testfile = get_module_resource(
            "l10n_ro_account_bank_statement_import_mt940_brd",
            "test_files",
            "test_brd_940.txt",
        )
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_brd")
        datafile = open(testfile, "rb").read()
        statements = parser.parse(datafile, header_lines=1)
        self._prepare_statement_lines(statements)
        self._load_statement(testfile, mt940_type="mt940_ro_brd")
        bank_statements = self.get_statements(self.journal.id)
        statement = bank_statements[0]
        transact = self.transactions[0]
        line = statement.line_ids[0]
        self.assertTrue(line.account_number == transact["account_number"])
        self.assertTrue(line.partner_name == transact["partner_name"])
        self.assertTrue(line.amount == transact["amount"])
        self.assertTrue(line.date == fields.Date.from_string("2016-05-17"))
        self.assertTrue(line.payment_ref == transact["payment_ref"])
        self.assertTrue(line.ref == transact["ref"])
