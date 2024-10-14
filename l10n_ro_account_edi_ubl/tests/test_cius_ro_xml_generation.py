# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


import freezegun

from odoo.tests import tagged

from .common_data_setup import CiusRoTestSetup


@tagged("post_install", "-at_install")
class TestCiusRoXmlGeneration(CiusRoTestSetup):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def get_attachment(self, move):
        if not move.ubl_cii_xml_id:
            xml_data, _build_errors = self.env[
                "account.edi.xml.ubl_ro"
            ]._export_invoice(move)
        else:
            xml_data = move.ubl_cii_xml_id.raw
        edi_doc = move._l10n_ro_edi_create_document_invoice_sending("123", xml_data)
        return edi_doc.attachment_id

    # invoice -> move_type = "out_invoice"
    @freezegun.freeze_time("2022-09-01")
    def test_account_invoice_edi_ubl(self):
        self.invoice.action_post()
        att = self.get_attachment(self.invoice)
        self._assert_invoice_attachment(
            att, xpaths=None, expected_file_path="invoice.xml"
        )

    # credit_note -> move_type = "out_refund"
    @freezegun.freeze_time("2022-09-01")
    def test_account_credit_note_edi_ubl(self):
        self.credit_note.action_post()
        att = self.get_attachment(self.credit_note)
        self._assert_invoice_attachment(
            att, xpaths=None, expected_file_path="credit_note.xml"
        )

    # credit_note with option -> move_type = "out_refund"
    @freezegun.freeze_time("2022-09-01")
    def test_account_credit_note_with_option_edi_ubl(self):
        self.env.company.l10n_ro_credit_note_einvoice = True
        self.credit_note.action_post()
        att = self.get_attachment(self.credit_note)
        self._assert_invoice_attachment(
            att, xpaths=None, expected_file_path="credit_note_option.xml"
        )

    # invoice -> move_type = "in_invoice"
    @freezegun.freeze_time("2022-09-01")
    def test_account_invoice_in_edi_ubl(self):
        self.invoice_in.action_post()
        att = self.get_attachment(self.invoice_in)
        self._assert_invoice_attachment(
            att, xpaths=None, expected_file_path="invoice_in.xml"
        )

    # credit_note -> move_type = "in_refund"
    @freezegun.freeze_time("2022-09-01")
    def test_account_credit_note_in_edi_ubl(self):
        self.credit_note_in.action_post()
        att = self.get_attachment(self.credit_note_in)
        self._assert_invoice_attachment(
            att, xpaths=None, expected_file_path="credit_note_in.xml"
        )

    # credit_note with option -> move_type = "in_refund"
    @freezegun.freeze_time("2022-09-01")
    def test_account_credit_note_in_with_option_edi_ubl(self):
        self.env.company.l10n_ro_credit_note_einvoice = True
        self.credit_note_in.action_post()
        att = self.get_attachment(self.credit_note_in)
        self._assert_invoice_attachment(
            att, xpaths=None, expected_file_path="credit_note_in_option.xml"
        )
