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

TESTFILE = (
    "l10n_ro_account_bank_statement_import_mt940_rffsn/test_files/test_rffsn_940.txt"
)


@tagged("post_install", "-at_install")
class TestImport(TestMT940BankStatementImport):
    def setUp(self):
        super().setUp()
        ron_curr = self.env.ref("base.RON")
        ron_curr.write({"active": True})
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

    def _parser(self, mt940_type="mt940_ro_rffsn"):
        return self.env[
            "l10n.ro.account.bank.statement.import.mt940.parser"
        ].with_context(type=mt940_type)

    def test_get_subfields(self):
        """Unit Test function get_subfields()."""
        res = self._parser().get_subfields(self.data, self.codewords)
        espected_res = {
            "20": ["F.2059628"],
            "24": ["Ref.Doc 2268/OPMC"],
            "30": ["RAIFFEIS EN BANK S.A."],
            "31": ["RO05RZBR0000060003144073"],
            "32": ["QUEHENBE RGER LOGISTICS ROU"],
        }
        self.assertTrue(res == espected_res)

    def test_handle_common_subfields(self):
        """Unit Test function handle_common_subfields()."""
        parser = self._parser()
        subfields = parser.get_subfields(self.data, self.codewords)
        transaction = self.transactions[0]
        parser.handle_common_subfields(transaction, subfields)

    def test_statement_import(self):
        """Test correct creation of single statement Raiffeisen."""
        testfile = file_path(TESTFILE)
        parser = self._parser()
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

    def test_is_rffsn(self):
        """The wizard must recognise a Raiffeisen statement both from the
        journal's BIC and from the explicit context flag, and stay out of the
        way otherwise."""
        self.bank.bank_id.bic = "RZBRROBU"
        wizard = self.env["account.statement.import"].with_context(
            journal_id=self.journal.id
        )
        self.assertTrue(wizard._is_rffsn())

        self.bank.bank_id.bic = "BRDEROBU"
        self.assertFalse(wizard._is_rffsn())

        wizard = self.env["account.statement.import"].with_context(mt940_ro_rffsn=True)
        self.assertTrue(wizard._is_rffsn())

        self.assertFalse(self.env["account.statement.import"]._is_rffsn())

    def test_parse_file_flagged_as_rffsn(self):
        """`_parse_file` must route through the Raiffeisen parser when the
        wizard is flagged as Raiffeisen, without the caller setting the parser
        `type` itself. This is the path a real import takes; passing `type`
        directly (as the other tests do) bypasses this module entirely and is
        served by the base module instead."""
        with open(file_path(TESTFILE), "rb") as datafile:
            data_file = datafile.read()
        wizard = self.env["account.statement.import"].with_context(mt940_ro_rffsn=True)
        currency, account_number, statements = wizard._parse_file(data_file)
        self.assertEqual(currency, "RON")
        self.assertEqual(account_number, "RO40RZBR0000060001111111")
        self.assertEqual(len(statements), 1)

        statement = statements[0]
        self.assertEqual(statement["balance_start"], 15564.52)
        self.assertEqual(statement["balance_end_real"], 16083.73)
        self.assertEqual(
            statement["date"], fields.Datetime.from_string("2012-06-18 00:00:00")
        )
        # Tag :NS: does not match the generic tag regex (it has no two digits),
        # so its content is appended to the record of the preceding :28C: tag
        # and ends up in the statement name.
        self.assertEqual(
            statement["name"],
            "108/1:NS:22ORDERING PARTY SA:23Cont curent Pachet Bronze RON",
        )
        self.assertEqual(len(statement["transactions"]), 3)

        incoming, payment, fee = statement["transactions"]
        self.assertEqual(incoming["amount"], 1179.87)
        self.assertEqual(incoming["account_number"], "RO05RZBR0000060003144073")
        self.assertEqual(incoming["partner_name"], "QUEHENBERGER LOGISTICS ROU")
        self.assertEqual(incoming["payment_ref"], "/F.2059628Ref.Doc 2268/OPMC")
        self.assertEqual(incoming["ref"], "11808959")
        self.assertEqual(
            incoming["date"], fields.Datetime.from_string("2012-06-18 00:00:00")
        )

        self.assertEqual(payment["amount"], -654.96)
        self.assertEqual(payment["account_number"], "RO38BRDE450SV88376004500")
        self.assertEqual(payment["partner_name"], "DANTE INTERNATIONAL SA")
        self.assertEqual(payment["payment_ref"], "/CV FP1046689Ref.Doc 18061/OPH")
        self.assertEqual(payment["ref"], "NONREF")

        # The fee line carries no counterpart, only a narrative.
        self.assertEqual(fee["amount"], -5.70)
        self.assertEqual(fee["payment_ref"], "/comision interbancar mica valoare CB")
        self.assertNotIn("account_number", fee)
        self.assertNotIn("partner_name", fee)

    def test_parse_file_falls_back_when_not_mt940(self):
        """A file the Raiffeisen parser cannot make sense of must be handed
        back to the generic import chain rather than swallowed."""
        wizard = self.env["account.statement.import"].with_context(mt940_ro_rffsn=True)
        with self.assertRaises(UserError):
            wizard._parse_file(b"this is not an MT940 file")

    def test_parser_does_not_hijack_other_banks(self):
        """Every Raiffeisen override must delegate to the generic parser for
        any other MT940 flavour. Without this, installing this module would
        break the import of every other bank in the same database."""
        rffsn = self._parser()
        other = self._parser("mt940_general")

        self.assertEqual(rffsn.get_header_lines(), 1)
        self.assertEqual(other.get_header_lines(), 0)
        self.assertEqual(rffsn.get_header_regex(), ":20:")
        self.assertEqual(other.get_header_regex(), ":940:")
        self.assertEqual(rffsn.get_subfield_split_text(), "^")
        self.assertEqual(other.get_subfield_split_text(), "/")
        self.assertIn("31", rffsn.get_codewords())
        self.assertNotIn("31", other.get_codewords())
        self.assertNotEqual(
            rffsn.get_tag_61_regex().pattern, other.get_tag_61_regex().pattern
        )
        # The Raiffeisen tag 61 regex carries a currency_type group the other
        # flavours do not have.
        self.assertIn("currency_type", rffsn.get_tag_61_regex().groupindex)
        self.assertNotIn("currency_type", other.get_tag_61_regex().groupindex)

        # get_subfields: "^" split for Raiffeisen, "/" split for the generic
        # parser
        self.assertEqual(
            rffsn.get_subfields("^20F.2059628", rffsn.get_codewords()),
            {"20": ["F.2059628"]},
        )
        self.assertNotIn(
            "20", other.get_subfields("^20F.2059628", other.get_codewords())
        )

        # handle_tag_28C falls through to the generic no-op
        result = {"statement": {"name": "keep me"}}
        other.handle_tag_28C("108/1", result)
        self.assertEqual(result["statement"]["name"], "keep me")

        # handle_common_subfields falls through to the generic codewords
        transaction = {}
        other.handle_common_subfields(transaction, {"EREF": ["X"]})
        self.assertEqual(transaction["payment_ref"], "/X")

        # handle_tag_62F falls through to the generic closing-balance handler
        result = {
            "statement": {"name": None, "date": None},
            "account_number": "RO40RZBR0000060001111111",
        }
        other.handle_tag_62F("C120618RON16083,73", result)
        self.assertEqual(result["statement"]["balance_end_real"], 16083.73)

    def test_handlers_skip_when_no_statement(self):
        """Both statement-scoped handlers guard on an open statement and must
        delegate when there is none."""
        rffsn = self._parser()
        result = {"statement": None, "account_number": None}
        self.assertEqual(rffsn.handle_tag_28C("108/1", result), result)
        self.assertEqual(rffsn.handle_tag_62F("C120618RON16083,73", result), result)

    def test_get_subfields_edge_cases(self):
        """A segment whose two-digit prefix is not a codeword continues the
        previous one -- note that its first two characters are dropped along
        with the (absent) codeword. Anything before the first codeword is
        dropped entirely."""
        rffsn = self._parser()
        codewords = rffsn.get_codewords()
        self.assertEqual(
            rffsn.get_subfields("^20F.2059628^99extra", codewords),
            {"20": ["F.2059628", "extra"]},
        )
        self.assertEqual(rffsn.get_subfields("^99orphan", codewords), {})

    def test_handle_common_subfields_counterparts(self):
        """Subfields 31/32/33 hold the counterpart. Spaces inside the IBAN
        (31) are squeezed out and the CUI/CNP marker is dropped."""
        rffsn = self._parser()
        transaction = {}
        rffsn.handle_common_subfields(
            transaction,
            {
                "31": ["RO05 RZBR 0000 0600 0314 4073"],
                "32": ["CUI/CNPQUEHENBERGER LOGISTICS ROU"],
                "20": ["F.2059628"],
            },
        )
        self.assertEqual(transaction["account_number"], "RO05RZBR0000060003144073")
        self.assertEqual(transaction["partner_name"], "QUEHENBERGER LOGISTICS ROU")
        self.assertEqual(transaction["payment_ref"], "/F.2059628")

        # With no counterpart subfield at all the transaction keeps only the
        # narrative.
        transaction = {}
        rffsn.handle_common_subfields(transaction, {"20": ["comision"]})
        self.assertNotIn("account_number", transaction)
        self.assertEqual(transaction["payment_ref"], "/comision")

        # The third counterpart subfield feeds partner_name when 32 is absent.
        transaction = {}
        rffsn.handle_common_subfields(
            transaction, {"31": ["RO05RZBR0000060003144073"], "33": ["FALLBACK NAME"]}
        )
        self.assertEqual(transaction["partner_name"], "FALLBACK NAME")

    def test_handle_common_subfields_ref_from_subfield(self):
        """When `ref` names one of the parsed subfields, it is replaced by
        that subfield's content."""
        rffsn = self._parser()
        transaction = {"ref": "20", "payment_ref": "keep"}
        rffsn.handle_common_subfields(transaction, {"20": ["F.2059628"]})
        self.assertEqual(transaction["ref"], "F.2059628")
        self.assertEqual(transaction["payment_ref"], "keepF.2059628")

    def test_handle_tag_28C_naming(self):
        """Tag 28C appends to a statement name already set, or sets it when
        the statement has none yet."""
        rffsn = self._parser()
        result = {"statement": {"name": "304210011"}}
        rffsn.handle_tag_28C("108/1", result)
        self.assertEqual(result["statement"]["name"], "304210011 - 108/1")

        result = {"statement": {"name": None}}
        rffsn.handle_tag_28C("108/1", result)
        self.assertEqual(result["statement"]["name"], "108/1")

    def test_handle_tag_62F_statement_naming(self):
        """A statement with no name of its own falls back to the account
        number, and a name that is the account number gets the closing date
        appended."""
        rffsn = self._parser()
        account = "RO40RZBR0000060001111111"

        result = {"statement": {"name": None, "date": None}, "account_number": account}
        rffsn.handle_tag_62F("C120618RON16083,73", result)
        self.assertEqual(result["statement"]["name"], account)
        self.assertEqual(result["statement"]["balance_end_real"], 16083.73)
        self.assertEqual(
            result["statement"]["date"],
            fields.Datetime.from_string("2012-06-18 00:00:00"),
        )

        result = {
            "statement": {"name": account, "date": None},
            "account_number": account,
        }
        rffsn.handle_tag_62F("C120618RON16083,73", result)
        self.assertEqual(result["statement"]["name"], f"{account} - 2012-06-18")

        # A name that is not the account number is left alone.
        result = {
            "statement": {"name": "108/1", "date": None},
            "account_number": account,
        }
        rffsn.handle_tag_62F("C120618RON16083,73", result)
        self.assertEqual(result["statement"]["name"], "108/1")
