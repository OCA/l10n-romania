# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools.misc import file_path

from odoo.addons.l10n_ro_account_bank_statement_import_mt940_base.tests.common import (
    TestMT940BankStatementImport,
)

TESTFILE = (
    "l10n_ro_account_bank_statement_import_mt940_exim/test_files/test_file_exim.mt940"
)


@tagged("post_install", "-at_install")
class TestImport(TestMT940BankStatementImport):
    def setUp(self):
        super().setUp()
        ron_curr = self.env.ref("base.RON")
        ron_curr.write({"active": True})
        self.bank = self.create_partner_bank("RO49BRMA1030025122260001")
        self.journal = self.create_journal("TBNK2MT940EXIM", self.bank, ron_curr)

    def _parser(self, mt940_type="mt940_ro_exim"):
        return self.env[
            "l10n.ro.account.bank.statement.import.mt940.parser"
        ].with_context(type=mt940_type)

    def _data_file(self):
        with open(file_path(TESTFILE), "rb") as datafile:
            return datafile.read()

    def _assert_parsed(self, currency, account_number, statements):
        """Assertions shared by the direct-parser and the wizard paths."""
        self.assertEqual(currency, "RON")
        self.assertEqual(account_number, "RO49BRMA1030025122260001")
        self.assertEqual(len(statements), 1)

        statement = statements[0]
        self.assertEqual(statement["name"], "26090")
        self.assertEqual(statement["balance_start"], 72759.07)
        self.assertEqual(statement["balance_end_real"], 52950.49)
        self.assertEqual(
            statement["date"], fields.Datetime.from_string("2026-03-31 00:00:00")
        )
        self.assertEqual(len(statement["transactions"]), 4)

        interest, fee, transfer, invoices = statement["transactions"]

        self.assertEqual(interest["amount"], -20505.68)
        self.assertEqual(interest["ref"], "00000001")
        self.assertEqual(interest["date"], fields.Date.from_string("2026-03-31"))
        self.assertIn("Rambursare dobanda", interest["payment_ref"])
        self.assertNotIn("Counterpart:", interest["payment_ref"])
        # No IBAN on the counterpart side for an internal interest line.
        self.assertNotIn("account_number", interest)

        self.assertEqual(fee["amount"], -3.00)
        self.assertEqual(fee["ref"], "00000002")
        self.assertEqual(fee["date"], fields.Date.from_string("2026-05-04"))
        self.assertIn("Incasare comision administrare cont curent", fee["payment_ref"])
        self.assertNotIn("Counterpart:", fee["payment_ref"])
        self.assertNotIn("account_number", fee)
        self.assertNotIn("partner_name", fee)

        self.assertEqual(transfer["amount"], 300.00)
        self.assertEqual(transfer["ref"], "00000003")
        self.assertEqual(transfer["date"], fields.Date.from_string("2026-05-27"))
        self.assertIn("Incasare OP", transfer["payment_ref"])
        self.assertNotIn("Counterpart:", transfer["payment_ref"])
        self.assertEqual(transfer["partner_name"], "NEXTERP ROMANIA SRL")
        self.assertEqual(transfer["account_number"], "RO32BRDE130SV76314662000")

        self.assertEqual(invoices["amount"], 400.10)
        self.assertEqual(invoices["ref"], "00000004")
        self.assertEqual(invoices["date"], fields.Date.from_string("2026-05-29"))
        self.assertIn("Incasare OP", invoices["payment_ref"])
        self.assertNotIn("Counterpart:", invoices["payment_ref"])
        self.assertEqual(invoices["partner_name"], "SMAROVIAL SOFTWARE S R L")
        self.assertEqual(invoices["account_number"], "RO21BTRL02202313W52723XX")

    def test_statement_import(self):
        """Test correct creation of single statement EXIM."""
        currency, account_number, statements = self._parser().parse(
            self._data_file(), header_lines=1
        )
        self._assert_parsed(currency, account_number, statements)

    def test_full_import(self):
        """Test the full import flow via account.statement.import."""
        self._load_statement(file_path(TESTFILE), mt940_type="mt940_ro_exim")
        bank_statements = self.get_statements(self.journal.id)
        self.assertTrue(bank_statements)
        statement = bank_statements[0]
        self.assertEqual(len(statement.line_ids), 4)

    def test_is_exim(self):
        """The wizard must recognise an Eximbank statement from either of the
        two BICs the bank operates under (Eximbank took over Banca
        Romaneasca), from the explicit context flag, and stay out of the way
        otherwise."""
        wizard = self.env["account.statement.import"]
        for bic in ("BRMAROBU", "EXIMROBU"):
            self.bank.bank_id.bic = bic
            self.assertTrue(
                wizard.with_context(journal_id=self.journal.id)._is_exim(),
                f"BIC {bic} must be recognised as Eximbank",
            )

        self.bank.bank_id.bic = "BRDEROBU"
        self.assertFalse(wizard.with_context(journal_id=self.journal.id)._is_exim())

        self.assertTrue(wizard.with_context(mt940_ro_exim=True)._is_exim())
        self.assertFalse(wizard._is_exim())

    def test_parse_file_flagged_as_exim(self):
        """`_parse_file` must route through the Eximbank parser when the
        wizard is flagged as such, without the caller setting the parser
        `type` itself. This is the path a real import takes; passing `type`
        directly bypasses this module entirely and is served by the base
        module instead."""
        wizard = self.env["account.statement.import"].with_context(mt940_ro_exim=True)
        currency, account_number, statements = wizard._parse_file(self._data_file())
        self._assert_parsed(currency, account_number, statements)

    def _wizard_for_new_company(self, acc_number=None):
        """A wizard bound to a fresh company, optionally owning a single bank
        account. Lets us drive both branches of the account remapping without
        touching the trusted account created in `setUp`."""
        company = self.env["res.company"].create({"name": "EXIM remap test"})
        if acc_number:
            self.env["res.partner.bank"].create(
                {
                    "acc_number": acc_number,
                    "partner_id": company.partner_id.id,
                    "company_id": company.id,
                }
            )
        return (
            self.env["account.statement.import"]
            .with_company(company)
            .with_context(mt940_ro_exim=True)
        )

    def test_parse_file_remaps_account_to_company_bank(self):
        """The account number read from the file is replaced by the matching
        company bank account, so the import lands on the right journal even
        when the file spells the IBAN differently."""
        wizard = self._wizard_for_new_company("RO49BRMA10300251222600010")
        _currency, account_number, _statements = wizard._parse_file(self._data_file())
        self.assertEqual(account_number, "RO49BRMA10300251222600010")

    def test_parse_file_keeps_account_when_no_company_bank(self):
        """With no company bank account matching the file, the number parsed
        from the file is kept as-is."""
        wizard = self._wizard_for_new_company()
        _currency, account_number, _statements = wizard._parse_file(self._data_file())
        self.assertEqual(account_number, "RO49BRMA1030025122260001")

    def test_parse_file_falls_back_when_not_mt940(self):
        """A file the Eximbank parser cannot make sense of must be handed back
        to the generic import chain rather than swallowed."""
        wizard = self.env["account.statement.import"].with_context(mt940_ro_exim=True)
        with self.assertRaises(UserError):
            wizard._parse_file(b"this is not an MT940 file")

    def test_parse_file_not_exim_delegates(self):
        """Without the Eximbank flag the wizard must not touch the file."""
        wizard = self.env["account.statement.import"]
        with self.assertRaises(UserError):
            wizard._parse_file(b"this is not an MT940 file")

    def test_partner_matching(self):
        """The counterpart is matched on the VAT number when the file carries
        one, and the Odoo partner name wins over the name spelled in the
        file."""
        partner = self.env["res.partner"].create(
            {"name": "NextERP Romania SRL", "vat": "RO39187746"}
        )
        _currency, _account_number, statements = self._parser().parse(self._data_file())
        transfer = statements[0]["transactions"][2]
        self.assertEqual(transfer["partner_id"], partner.id)
        self.assertEqual(transfer["partner_name"], "NextERP Romania SRL")

    def test_header_regex_accepts_swift_envelope(self):
        """Eximbank files start with the SWIFT `{1:` envelope, not with the
        `:20:` tag. Since 18.0 the base parser anchors the header regex at the
        start of the data, so a `:20:` header regex silently yields no
        statement at all."""
        parser = self._parser()
        self.assertEqual(parser.get_header_regex(), "^{1:")
        self.assertEqual(parser.get_header_lines(), 1)
        data = self._data_file().decode()
        self.assertTrue(data.startswith("{1:"))
        self.assertTrue(parser.is_mt940(data))
        self.assertEqual(len(parser.pre_process_data(data)), 1)

    def test_parser_does_not_hijack_other_banks(self):
        """Every Eximbank override must delegate to the generic parser for any
        other MT940 flavour. Without this, installing this module would break
        the import of every other bank in the same database."""
        exim = self._parser()
        other = self._parser("mt940_general")

        self.assertEqual(exim.get_header_lines(), 1)
        self.assertEqual(other.get_header_lines(), 0)
        self.assertEqual(exim.get_header_regex(), "^{1:")
        self.assertEqual(other.get_header_regex(), ":940:")
        self.assertNotEqual(
            exim.get_tag_61_regex().pattern, other.get_tag_61_regex().pattern
        )

        # handle_tag_28C falls through to the generic no-op
        result = {"statement": {"name": "keep me"}}
        other.handle_tag_28C("26090", result)
        self.assertEqual(result["statement"]["name"], "keep me")

        # handle_tag_61 falls through to the generic transaction handler
        result = {"statement": {"transactions": []}}
        other.handle_tag_61("160517C1000,00NTRFNONREF", result)
        self.assertEqual(len(result["statement"]["transactions"]), 1)
        self.assertEqual(result["statement"]["transactions"][0]["amount"], 1000.0)

        # handle_tag_86 falls through to the generic subfield handler
        other.handle_tag_86("/EREF/X", result)
        self.assertEqual(result["statement"]["transactions"][0]["payment_ref"], "/X")

    def test_handle_tag_28C_appends_to_existing_name(self):
        """Tag 28C extends a statement name already set by tag 20. In a real
        Eximbank file tag 20 is consumed as a header line, so this path only
        shows up when the header is handled differently."""
        parser = self._parser()
        result = {"statement": {"name": "00000001"}}
        parser.handle_tag_28C("26090", result)
        self.assertEqual(result["statement"]["name"], "00000001 - 26090")

        # No statement yet: nothing to name.
        result = {"statement": None}
        parser.handle_tag_28C("26090", result)
        self.assertIsNone(result["statement"])

    def test_handle_tag_61_ignores_unparsable_line(self):
        """A tag 61 line that does not match the Eximbank layout must not
        create a transaction."""
        parser = self._parser()
        result = {"statement": {"transactions": []}}
        parser.handle_tag_61("garbage", result)
        self.assertEqual(result["statement"]["transactions"], [])

        # A well-formed line with no statement open is dropped too.
        result = {"statement": None}
        parser.handle_tag_61(
            "2603310331DN20505,68NMSCNONREF          //00000001", result
        )
        self.assertIsNone(result["statement"])

    def test_handle_tag_86_without_transaction(self):
        """Tag 86 details belong to the preceding transaction; with none open
        the record is ignored."""
        parser = self._parser()
        result = {"statement": {"transactions": []}}
        parser.handle_tag_86("Counterpart:/Plata", result)
        self.assertEqual(result["statement"]["transactions"], [])

        result = {"statement": None}
        parser.handle_tag_86("Counterpart:/Plata", result)
        self.assertIsNone(result["statement"])

    def test_handle_tag_86_appends_to_existing_narration(self):
        """A second tag 86 record for the same transaction extends the
        narration instead of replacing it."""
        parser = self._parser()
        transaction = {}
        result = {"statement": {"transactions": [transaction]}}
        parser.handle_tag_86("Counterpart:/Prima linie", result)
        self.assertEqual(transaction["narration"], "Prima linie")
        parser.handle_tag_86("Counterpart:/A doua linie", result)
        self.assertEqual(transaction["narration"], "A doua linie - Prima linie")

    def test_handle_tag_86_plain_narrative(self):
        """Tag 86 without the `Counterpart:` prefix, without a company suffix
        and without an IBAN yields only the description."""
        parser = self._parser()
        transaction = {}
        result = {"statement": {"transactions": [transaction]}}
        parser.handle_tag_86("Comision   lunar", result)
        self.assertEqual(transaction["payment_ref"], "Comision lunar")
        self.assertEqual(transaction["narration"], "Comision lunar")
        self.assertNotIn("partner_name", transaction)
        self.assertNotIn("account_number", transaction)

    def test_handle_tag_86_empty_description(self):
        """An empty tag 86 still gets the placeholder payment reference the
        rest of the import chain expects."""
        parser = self._parser()
        transaction = {}
        result = {"statement": {"transactions": [transaction]}}
        parser.handle_tag_86("Counterpart:/", result)
        self.assertEqual(transaction["payment_ref"], "/")

    def test_extract_helpers(self):
        """Unit coverage for the three Eximbank-specific extractors, on both
        the matching and the non-matching branch."""
        parser = self._parser()

        self.assertEqual(
            parser._extract_exim_partner("Incasare OP NEXTERP ROMANIA SRL"),
            "Incasare OP NEXTERP ROMANIA SRL",
        )
        self.assertFalse(parser._extract_exim_partner("incasare op fara firma"))

        self.assertEqual(
            parser._extract_exim_partner_cif("/NEXTERP ROMANIA SRL/39187746 /"),
            "39187746",
        )
        self.assertFalse(
            parser._extract_exim_partner_cif("//2026526162610645/NEXTERP/")
        )

        self.assertEqual(
            parser._extract_exim_partner_bank_account(
                "Counterpart:RO32BRDE130SV76314662000/Incasare OP"
            ),
            "RO32BRDE130SV76314662000",
        )
        self.assertFalse(
            parser._extract_exim_partner_bank_account("Counterpart:/Incasare OP")
        )
