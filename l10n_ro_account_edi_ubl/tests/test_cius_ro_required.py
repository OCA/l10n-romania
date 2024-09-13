# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from .common_data_setup import CiusRoTestSetup


@tagged("post_install", "-at_install")
class TestCiusRoRequired(CiusRoTestSetup):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_is_required_for_invoice_out_invoice(self):
        self.assertTrue(self.invoice._need_ubl_cii_xml())

    def test_is_required_for_invoice_out_refund(self):
        self.assertTrue(self.credit_note._need_ubl_cii_xml())

    def test_is_required_for_invoice_in_invoice(self):
        self.assertTrue(self.invoice_in._need_ubl_cii_xml())

    def test_is_required_for_invoice_in_refund(self):
        self.assertTrue(self.credit_note_in._need_ubl_cii_xml())

    def test_is_required_for_invoice_non_ro_partner(self):
        self.invoice.commercial_partner_id.country_id = self.env.ref("base.us")
        self.assertFalse(self.invoice._need_ubl_cii_xml())

    def test_is_required_for_invoice_non_company_partner(self):
        self.invoice.commercial_partner_id.is_company = False
        self.assertFalse(self.invoice._need_ubl_cii_xml())

    def test_is_required_for_invoice_missing_partner_id(self):
        self.invoice_in.journal_id.l10n_ro_partner_id = False
        self.assertFalse(self.invoice_in._need_ubl_cii_xml())

    def test_is_required_for_partner_no_cius_option(self):
        # Test when the partner has ubl_cii_format set to False
        self.invoice.commercial_partner_id.ubl_cii_format = False
        self.assertFalse(self.invoice._need_ubl_cii_xml())
