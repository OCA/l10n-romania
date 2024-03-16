# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64

import freezegun

from odoo.tests import tagged

from .common_data_setup import CiusRoTestSetup


@tagged("post_install", "-at_install")
class TestCiusRoXmlGeneration(CiusRoTestSetup):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.edi_cius_format = cls.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")

    # invoice -> move_type = "out_invoice"
    @freezegun.freeze_time("2022-09-01")
    def test_account_invoice_edi_ubl(self):
        self.invoice.action_post()
        invoice_xml = self.invoice.attach_ubl_xml_file_button()
        att = self.env["ir.attachment"].browse(invoice_xml["res_id"])
        xml_content = base64.b64decode(att.with_context(bin_size=False).datas)

        current_etree = self.get_xml_tree_from_string(xml_content)
        expected_etree = self.get_xml_tree_from_string(self.get_file("invoice.xml"))
        self.assertXmlTreeEqual(current_etree, expected_etree)

    # credit_note -> move_type = "out_refund"
    @freezegun.freeze_time("2022-09-01")
    def test_account_credit_note_edi_ubl(self):
        self.credit_note.action_post()
        invoice_xml = self.credit_note.attach_ubl_xml_file_button()
        att = self.env["ir.attachment"].browse(invoice_xml["res_id"])
        xml_content = base64.b64decode(att.with_context(bin_size=False).datas)

        current_etree = self.get_xml_tree_from_string(xml_content)
        expected_etree = self.get_xml_tree_from_string(self.get_file("credit_note.xml"))
        self.assertXmlTreeEqual(current_etree, expected_etree)

    # credit_note with option -> move_type = "out_refund"
    @freezegun.freeze_time("2022-09-01")
    def test_account_credit_note_with_option_edi_ubl(self):
        self.credit_note.action_post()
        self.env.company.l10n_ro_credit_note_einvoice = True
        invoice_xml = self.credit_note.attach_ubl_xml_file_button()
        att = self.env["ir.attachment"].browse(invoice_xml["res_id"])
        xml_content = base64.b64decode(att.with_context(bin_size=False).datas)

        current_etree = self.get_xml_tree_from_string(xml_content)
        expected_etree = self.get_xml_tree_from_string(
            self.get_file("credit_note_option.xml")
        )
        self.assertXmlTreeEqual(current_etree, expected_etree)

    # invoice -> move_type = "in_invoice"
    @freezegun.freeze_time("2022-09-01")
    def test_account_invoice_in_edi_ubl(self):
        self.invoice_in.action_post()
        invoice_xml = self.invoice_in.attach_ubl_xml_file_button()
        att = self.env["ir.attachment"].browse(invoice_xml["res_id"])
        xml_content = base64.b64decode(att.with_context(bin_size=False).datas)

        current_etree = self.get_xml_tree_from_string(xml_content)
        expected_etree = self.get_xml_tree_from_string(self.get_file("invoice_in.xml"))
        self.assertXmlTreeEqual(current_etree, expected_etree)

    # credit_note -> move_type = "in_refund"
    @freezegun.freeze_time("2022-09-01")
    def test_account_credit_note_in_edi_ubl(self):
        self.credit_note_in.action_post()
        invoice_xml = self.credit_note_in.attach_ubl_xml_file_button()
        att = self.env["ir.attachment"].browse(invoice_xml["res_id"])
        xml_content = base64.b64decode(att.with_context(bin_size=False).datas)

        current_etree = self.get_xml_tree_from_string(xml_content)
        expected_etree = self.get_xml_tree_from_string(
            self.get_file("credit_note_in.xml")
        )
        self.assertXmlTreeEqual(current_etree, expected_etree)

    # credit_note with option -> move_type = "in_refund"
    @freezegun.freeze_time("2022-09-01")
    def test_account_credit_note_in_with_option_edi_ubl(self):
        self.credit_note_in.action_post()
        self.env.company.l10n_ro_credit_note_einvoice = True
        invoice_xml = self.credit_note_in.attach_ubl_xml_file_button()
        att = self.env["ir.attachment"].browse(invoice_xml["res_id"])
        xml_content = base64.b64decode(att.with_context(bin_size=False).datas)

        current_etree = self.get_xml_tree_from_string(xml_content)
        expected_etree = self.get_xml_tree_from_string(
            self.get_file("credit_note_in_option.xml")
        )
        self.assertXmlTreeEqual(current_etree, expected_etree)
