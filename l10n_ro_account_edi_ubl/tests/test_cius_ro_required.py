# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from .common_data_setup import CiusRoTestSetup


@tagged("post_install", "-at_install")
class TestCiusRoRequired(CiusRoTestSetup):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.edi_cius_format = cls.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")

    def test_is_compatible_with_journal_sale_ro(self):
        is_compatible = self.edi_cius_format._is_compatible_with_journal(
            self.invoice.journal_id
        )
        self.assertTrue(is_compatible)

    def test_is_compatible_with_journal_purchase_autoinv2(self):
        is_compatible = self.edi_cius_format._is_compatible_with_journal(
            self.journal_CIUS
        )
        self.assertTrue(is_compatible)

    def test_is_compatible_with_journal_not_compatible(self):
        self.env.company.account_fiscal_country_id = self.env.ref("base.us")
        journal = self.env["account.journal"].create(
            {
                "name": "Test Journal",
                "code": "TJ-TEST",
                "type": "sale",
                "company_id": self.env.company.id,
                "default_account_id": self.company_data["default_account_revenue"].id,
            }
        )
        is_compatible = self.edi_cius_format._is_compatible_with_journal(journal)
        self.assertFalse(is_compatible)

    def test_is_required_for_invoice_out_invoice(self):
        self.assertTrue(self.edi_cius_format._is_required_for_invoice(self.invoice))

    def test_is_required_for_invoice_out_refund(self):
        self.assertTrue(self.edi_cius_format._is_required_for_invoice(self.credit_note))

    def test_is_required_for_invoice_in_invoice(self):
        self.assertTrue(self.edi_cius_format._is_required_for_invoice(self.invoice_in))

    def test_is_required_for_invoice_in_refund(self):
        self.assertTrue(
            self.edi_cius_format._is_required_for_invoice(self.credit_note_in)
        )

    def test_is_required_for_invoice_non_ro_partner(self):
        self.invoice.commercial_partner_id.country_id = self.env.ref("base.us")
        self.assertFalse(self.edi_cius_format._is_required_for_invoice(self.invoice))

    def test_is_required_for_invoice_non_company_partner(self):
        self.invoice.commercial_partner_id.is_company = False
        self.assertFalse(self.edi_cius_format._is_required_for_invoice(self.invoice))

    def test_is_required_for_invoice_missing_partner_id(self):
        self.invoice_in.journal_id.l10n_ro_partner_id = False
        self.assertFalse(self.edi_cius_format._is_required_for_invoice(self.invoice_in))

    def test_get_l10n_ro_edi_invoice_needed_invoice(self):
        # Test when move_type is out_invoice, commercial_partner_id is a company in Romania
        self.assertTrue(self.invoice.get_l10n_ro_edi_invoice_needed())

    def test_get_l10n_ro_edi_invoice_needed_credit_note(self):
        # Test when move_type is out_refund, commercial_partner_id is a company in Romania
        self.assertTrue(self.credit_note.get_l10n_ro_edi_invoice_needed())

    def test_get_l10n_ro_edi_invoice_needed_invoice_in(self):
        # Test when move_type is in_invoice, journal_id has l10n_ro_sequence_type as
        # "autoinv2" and l10n_ro_partner_id is set
        self.assertTrue(self.invoice_in.get_l10n_ro_edi_invoice_needed())

    def test_get_l10n_ro_edi_invoice_needed_credit_note_in(self):
        # Test when move_type is in_refund, journal_id has l10n_ro_sequence_type as "autoinv2"
        # and l10n_ro_partner_id is set
        self.assertTrue(self.credit_note_in.get_l10n_ro_edi_invoice_needed())

    def test_get_l10n_ro_edi_invoice_not_needed_invoice(self):
        # Test when move_type is not in the specified types and conditions are not met
        self.invoice.commercial_partner_id.is_company = False
        self.assertFalse(self.invoice.get_l10n_ro_edi_invoice_needed())

    def test_get_l10n_ro_edi_invoice_not_needed_invoice_in(self):
        # Test when move_type is not in the specified types and conditions are not met
        self.invoice_in.journal_id.l10n_ro_partner_id = False
        self.assertFalse(self.invoice_in.get_l10n_ro_edi_invoice_needed())

    def test_get_l10n_ro_edi_invoice_needed_partner_option(self):
        # Test when the partner has l10n_ro_edi_ubl_no_send set to True
        self.invoice.commercial_partner_id.l10n_ro_edi_ubl_no_send = True
        self.assertFalse(self.invoice.get_l10n_ro_edi_invoice_needed())
