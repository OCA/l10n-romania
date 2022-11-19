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
        self.bank = self.create_partner_bank("RO87BUCU1052235283028")
        self.journal = self.create_journal("TBNK2MT940", self.bank, ron_curr)

        self.data = """IB - Plata intrabancara BENEFICIA
R  NEXTERP ROMANIA SRL BUCUROBU RO65BUCU078823522511RO01 DETALII
 PLATA  105IBAB22300004T cv fact 2004   CUST REFERENCE   902 """
        self.codewords = ["BENEFICIAR", "PLATITOR", "DETALII", "CUST REFERENCE"]
        self.transactions = [
            {
                "account_number": "RO88BTRLRONCRT0301398801",
                "partner_name": "NEXTERP ROMANIA SRL",
                "amount": 1000.0,
                "payment_ref": " INCASARE  .ROC.rata SIS..RFB.22 NOTPROVIDED   END "
                "TO END ID  NOTPROVIDED ",
                "ref": "   032EPOH223040543",
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
        parser = parser.with_context(type="mt940_ro_alpha")
        res = parser.get_subfields(self.data, self.codewords)
        espected_res = {
            "BENEFICIAR": [
                "",
                "NEXTERP",
                "ROMANIA",
                "SRL",
                "BUCUROBU",
                "RO65BUCU078823522511RO01",
            ],
            "DETALII": [
                "PLATA",
                "",
                "105IBAB22300004T",
                "cv",
                "fact",
                "2004",
                "",
                "",
                "CUST",
                "REFERENCE",
                "",
                "",
                "902",
                "",
            ],
        }

        self.assertTrue(res == espected_res)

    def test_handle_common_subfields(self):
        """Unit Test function handle_common_subfields()."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_alpha")
        subfields = parser.get_subfields(self.data, self.codewords)
        transaction = self.transactions[0]
        parser.handle_common_subfields(transaction, subfields)

    def test_statement_import(self):
        """Test correct creation of single statement BCR."""
        testfile = get_module_resource(
            "l10n_ro_account_bank_statement_import_mt940_alpha",
            "test_files",
            "test_alpha_940.txt",
        )
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_alpha")
        datafile = open(testfile, "rb").read()
        statements = parser.parse(datafile, header_lines=1)
        self._prepare_statement_lines(statements)
        self._load_statement(testfile, mt940_type="mt940_ro_alpha")
        bank_statements = self.get_statements(self.journal.id)
        statement = bank_statements[0]
        transact = self.transactions[0]
        line = statement.line_ids[0]
        self.assertTrue(line.account_number == transact["account_number"])
        self.assertTrue(line.partner_name == transact["partner_name"])
        self.assertTrue(line.amount == transact["amount"])
        self.assertTrue(line.date == fields.Date.from_string("2022-11-01"))
        self.assertTrue(line.payment_ref == transact["payment_ref"])
        self.assertTrue(line.ref == transact["ref"])
