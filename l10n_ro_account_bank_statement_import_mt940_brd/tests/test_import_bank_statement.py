# Copyright (C) 2016 Forest and Biomass Romania
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields
from odoo.exceptions import UserError
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
            "20": ["Plata"],
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
        testfile = file_path(
            "l10n_ro_account_bank_statement_import_mt940_brd/test_files/test_brd_940.txt",
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

    def test_is_brd(self):
        """The wizard must recognise a BRD statement both from the journal's
        BIC and from the explicit context flag, and stay out of the way
        otherwise."""
        self.bank.bank_id.bic = "BRDEROBU"
        wizard = self.env["account.statement.import"].with_context(
            journal_id=self.journal.id
        )
        self.assertTrue(wizard._is_brd())

        wizard = self.env["account.statement.import"].with_context(mt940_ro_brd=True)
        self.assertTrue(wizard._is_brd())

        self.assertFalse(self.env["account.statement.import"]._is_brd())

    def test_parse_file_flagged_as_brd(self):
        """`_parse_file` must route through the BRD parser when the wizard is
        flagged as BRD, without the caller setting the parser `type` itself.
        This is the path a real import takes; passing `type` directly (as the
        other tests do) bypasses this module entirely and is served by the
        base module instead."""
        testfile = file_path(
            "l10n_ro_account_bank_statement_import_mt940_brd/test_files/test_brd_940.txt",
        )
        with open(testfile, "rb") as datafile:
            data_file = datafile.read()
        wizard = self.env["account.statement.import"].with_context(mt940_ro_brd=True)
        currency, account_number, statements = wizard._parse_file(data_file)
        self.assertEqual(currency, "RON")
        self.assertEqual(account_number, "RO56BRDE360SV52474653600")
        self.assertEqual(len(statements), 1)

        statement = statements[0]
        self.assertEqual(statement["name"], "00138/1")
        self.assertEqual(statement["balance_start"], 1000.0)
        self.assertEqual(statement["balance_end_real"], 1998.0)
        self.assertEqual(len(statement["transactions"]), 2)

        payment, fee = statement["transactions"]
        self.assertEqual(payment["amount"], 1000.0)
        self.assertEqual(payment["partner_name"], "NEXTERP ROMANIA SRL")
        self.assertEqual(payment["account_number"], "RO89RZBR0000060003480121")
        self.assertEqual(payment["payment_ref"], "/PLATA FACT 4603309")
        self.assertEqual(payment["ref"], "OPH478PLATA")
        # The fee line carries no counterpart, only a narrative.
        self.assertEqual(fee["amount"], -2.0)
        self.assertEqual(fee["payment_ref"], "/25-Comision MULTIX")
        self.assertNotIn("account_number", fee)
        self.assertNotIn("partner_name", fee)

    def test_parse_file_falls_back_when_not_mt940(self):
        """A file the BRD parser cannot make sense of must be handed back to
        the generic import chain rather than swallowed."""
        wizard = self.env["account.statement.import"].with_context(mt940_ro_brd=True)
        with self.assertRaises(UserError):
            wizard._parse_file(b"this is not an MT940 file")

    def test_parser_does_not_hijack_other_banks(self):
        """Every BRD override must delegate to the generic parser for any
        other MT940 flavour. Without this, installing the BRD module would
        break the import of every other bank in the same database."""
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        brd = parser.with_context(type="mt940_ro_brd")
        other = parser.with_context(type="mt940_general")

        self.assertEqual(brd.get_header_lines(), 1)
        self.assertEqual(other.get_header_lines(), 0)
        self.assertEqual(brd.get_header_regex(), ":20:")
        self.assertEqual(other.get_header_regex(), ":940:")
        self.assertEqual(brd.get_subfield_split_text(), "+")
        self.assertEqual(other.get_subfield_split_text(), "/")
        self.assertIn("31", brd.get_codewords())
        self.assertNotIn("31", other.get_codewords())
        self.assertNotEqual(
            brd.get_tag_61_regex().pattern, other.get_tag_61_regex().pattern
        )

        # get_subfields: "+" split for BRD, "/" split for the generic parser
        self.assertEqual(
            brd.get_subfields("+20Plata", brd.get_codewords()), {"20": ["Plata"]}
        )
        self.assertNotIn("20", other.get_subfields("+20Plata", other.get_codewords()))

        # handle_tag_28 falls through to the generic no-op
        result = {"statement": {"name": "keep me"}}
        other.handle_tag_28("00138/1", result)
        self.assertEqual(result["statement"]["name"], "keep me")

        # handle_common_subfields falls through to the generic codewords
        transaction = {}
        other.handle_common_subfields(transaction, {"EREF": ["X"]})
        self.assertEqual(transaction["payment_ref"], "/X")

        # handle_tag_62F falls through to the generic closing-balance handler
        result = {
            "statement": {"name": None, "date": None},
            "account_number": "RO56BRDE360SV52474653600",
        }
        other.handle_tag_62F("C160517RON1998,00", result)
        self.assertEqual(result["statement"]["balance_end_real"], 1998.0)

    def test_get_subfields_edge_cases(self):
        """A leading separator yields an empty first segment, and a segment
        whose two-digit prefix is not a codeword continues the previous
        one."""
        subfields = self.env[
            "l10n.ro.account.bank.statement.import.mt940.parser"
        ].with_context(type="mt940_ro_brd")
        codewords = subfields.get_codewords()
        self.assertEqual(
            subfields.get_subfields("+20Plata+99extra", codewords),
            {"20": ["Plata", "extra"]},
        )

    def test_handle_common_subfields_ref_from_subfield(self):
        """When `ref` names one of the parsed subfields, it is replaced by
        that subfield's content."""
        parser = self.env[
            "l10n.ro.account.bank.statement.import.mt940.parser"
        ].with_context(type="mt940_ro_brd")
        transaction = {"ref": "20"}
        parser.handle_common_subfields(transaction, {"20": ["Plata"], "23": ["FACT"]})
        self.assertEqual(transaction["ref"], "Plata")
        self.assertEqual(transaction["payment_ref"], "/FACT")

    def test_handle_tag_28_appends_to_existing_name(self):
        """Tag 28 extends a statement name already set by tag 20. In a real
        BRD file tag 20 is consumed as a header line, so this path only shows
        up when the header is handled differently."""
        parser = self.env[
            "l10n.ro.account.bank.statement.import.mt940.parser"
        ].with_context(type="mt940_ro_brd")
        result = {"statement": {"name": "6450374100"}}
        parser.handle_tag_28("00138/1", result)
        self.assertEqual(result["statement"]["name"], "6450374100 - 00138/1")

    def test_handle_tag_62F_statement_naming(self):
        """A statement with no name of its own falls back to the account
        number, and a name that is the account number gets the closing date
        appended."""
        parser = self.env[
            "l10n.ro.account.bank.statement.import.mt940.parser"
        ].with_context(type="mt940_ro_brd")
        account = "RO56BRDE360SV52474653600"

        result = {"statement": {"name": None, "date": None}, "account_number": account}
        parser.handle_tag_62F("C160517RON1998,00", result)
        self.assertEqual(result["statement"]["name"], account)
        self.assertEqual(result["statement"]["balance_end_real"], 1998.0)
        self.assertEqual(
            result["statement"]["date"],
            fields.Datetime.from_string("2016-05-17 00:00:00"),
        )

        result = {
            "statement": {"name": account, "date": None},
            "account_number": account,
        }
        parser.handle_tag_62F("C160517RON1998,00", result)
        self.assertEqual(result["statement"]["name"], f"{account} - 2016-05-17")
