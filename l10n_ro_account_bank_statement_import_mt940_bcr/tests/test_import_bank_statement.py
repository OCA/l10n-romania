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
                "payment_ref": "  /ROC/SERIA BTLAM NR 21036843 . . /RFB/31/20221028/20221031",  # noqa
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
        testfile = file_path(
            "l10n_ro_account_bank_statement_import_mt940_bcr/test_files/test_file_bcr.STA",
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

    def test_is_bcr(self):
        """Test _is_bcr function."""
        # Create a journal with BCR BIC
        bank = self.create_partner_bank("RO48RNCB0090000506460002")
        bank.bank_id.bic = "RNCBROBU"
        journal = self.create_journal("BCRJRNL", bank, self.env.ref("base.RON"))

        wizard = self.env["account.statement.import"].with_context(
            journal_id=journal.id
        )
        self.assertTrue(wizard._is_bcr())

        wizard = self.env["account.statement.import"].with_context(mt940_ro_bcr=True)
        self.assertTrue(wizard._is_bcr())

    def test_handle_tag_28(self):
        """Test handle_tag_28 for statement name."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_bcr")
        result = {"statement": {"name": None}}
        parser.handle_tag_28("00015/00001.", result)
        self.assertEqual(result["statement"]["name"], "00015/00001")

    def test_get_counterpart_variants(self):
        """Test get_counterpart with different subfield lengths."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_bcr")

        # Length 1
        transaction = {}
        parser.get_counterpart(transaction, ["ACC123"])
        self.assertEqual(transaction.get("account_number"), "ACC123")

        # Length 2
        transaction = {}
        parser.get_counterpart(transaction, ["ACC123", "PARTNER NAME"])
        self.assertEqual(transaction.get("partner_name"), "PARTNER NAME")

    def test_handle_tag_86_variants(self):
        """Test handle_tag_86 with various data formats."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_bcr")

        # variant 1: ref + p + cfp + b + cfb + d
        data = (
            "Referinta 1234567890123456"
            "Platitor PARTNER P RO48RNCB0090000506460001"
            "CODFISC 12345"
            "Beneficiar PARTNER B RO48RNCB0090000506460002"
            "CODFISC 67890"
            "Detalii SOME DETAILS"
        )
        result = {"statement": {"transactions": [{"amount": 100.0}]}}
        parser.handle_tag_86(data, result)
        transaction = result["statement"]["transactions"][0]
        self.assertEqual(transaction["ref"], "1234567890123456")
        self.assertEqual(transaction["partner_name"], "PARTNER P")
        self.assertEqual(transaction["account_number"], "RO48RNCB0090000506460001")

        # variant 3: ref + p + b + d
        data = (
            "Referinta 1234567890123456"
            "Platitor PARTNER P RO48RNCB0090000506460001"
            "Beneficiar PARTNER B RO48RNCB0090000506460002"
            "Detalii SOME DETAILS"
        )
        result = {"statement": {"transactions": [{"amount": -100.0}]}}
        parser.handle_tag_86(data, result)
        transaction = result["statement"]["transactions"][0]
        self.assertEqual(transaction["partner_name"], "PARTNER B")
        self.assertEqual(transaction["account_number"], "RO48RNCB0090000506460002")

        # variant 5: ref + b + p
        data = (
            "Referinta 1234567890123456"
            "Beneficiar PARTNER B RO48RNCB0090000506460002"
            "Platitor PARTNER P RO48RNCB0090000506460001"
        )
        result = {"statement": {"transactions": [{"amount": -100.0}]}}
        parser.handle_tag_86(data, result)
        transaction = result["statement"]["transactions"][0]
        self.assertEqual(transaction["partner_name"], "PARTNER B")
        self.assertEqual(transaction["account_number"], "RO48RNCB0090000506460002")

        # No match regex
        data = "Random data without codewords"
        result = {"statement": {"transactions": [{"amount": 100.0}]}}
        parser.handle_tag_86(data, result)
        transaction = result["statement"]["transactions"][0]
        self.assertEqual(transaction["payment_ref"], data)

        # Test with transaction already having a name (should skip regex)
        data = "Referinta 9999999999999999"
        result = {
            "statement": {"transactions": [{"amount": 100.0, "name": "ALREADY SET"}]}
        }
        parser.handle_tag_86(data, result)
        transaction = result["statement"]["transactions"][0]
        self.assertNotEqual(transaction.get("ref"), "9999999999999999")

    def test_post_parse_file_vat_search(self):
        """Test _post_parse_file search partner by VAT."""
        partner = self.env["res.partner"].create(
            {"name": "VAT PARTNER POST", "vat": "RO999999", "is_company": True}
        )
        wizard = self.env["account.statement.import"]
        data = (
            "RON",
            "ACC123",
            [
                {
                    "transactions": [
                        {"amount": 100.0, "vat": "RO999999"},
                        {"amount": -50.0, "vat": "INVALID"},
                    ]
                }
            ],
        )
        res = wizard._post_parse_file(data)
        transactions = res[2][0]["transactions"]
        self.assertEqual(transactions[0]["partner_id"], partner.id)
        self.assertEqual(transactions[0]["partner_name"], partner.name)
        self.assertNotIn("vat", transactions[0])
        self.assertFalse(transactions[1].get("partner_id"))

    def test_handle_tag_86_vat_search(self):
        """Test handle_tag_86 search partner by VAT."""
        unique_vat = "RO12345678"
        partner = self.env["res.partner"].create(
            {"name": "VAT PARTNER", "vat": unique_vat, "is_company": True}
        )
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_bcr")

        # Data containing the unique VAT
        data = (
            "Referinta 1234567890123456"
            "Platitor VAT PARTNER RO48RNCB0090000506460001"
            "CODFISC 12345678"  # Regex for codfis_p is \w+
            "Beneficiar PARTNER B RO48RNCB0090000506460002"
            "CODFISC 67890"
            "Detalii SOME DETAILS"
        )
        # Note: BCR logic for VAT search uses parsed_data.get("codfis_p")
        # and searches for vat = unique_vat.
        # But wait, unique_vat has "RO" prefix, but codfisc from bank usually doesn't.
        # BCR code does: domain = [("vat", "=", vat), ("is_company", "=", True)]
        # So I should create the partner with vat="12345678" if codfisc is "12345678"
        partner.vat = "12345678"

        result = {"statement": {"transactions": [{"amount": 100.0}]}}
        parser.handle_tag_86(data, result)
        transaction = result["statement"]["transactions"][0]
        self.assertEqual(transaction.get("partner_id"), partner.id)
        self.assertEqual(transaction.get("partner_name"), "VAT PARTNER")

    def test_handle_tag_61(self):
        """Test handle_tag_61 regex and extraction."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        parser = parser.with_context(type="mt940_ro_bcr")
        result = {"statement": {"transactions": []}}
        # 221031 (date) 1031 (line_date) C (sign) 1000,00 (amount)
        # NTRF (type) .//2022103180931993 (ref)
        data = "2210311031C1000,00NTRF.//2022103180931993Test Partner"
        parser.handle_tag_61(data, result)
        transaction = result["statement"]["transactions"][0]
        self.assertEqual(transaction["amount"], 1000.0)
        self.assertEqual(transaction["ref"], "2022103180931993")
