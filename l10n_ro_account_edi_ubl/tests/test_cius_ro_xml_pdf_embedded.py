# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64

from odoo.tests.common import tagged

from .common_data_setup import CiusRoTestSetup


@tagged("post_install", "-at_install")
class TestCiusRoXMLPDFEmbedded(CiusRoTestSetup):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.edi_cius_format = cls.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")

    def check_xml_pdf_embedded(self, pdf):
        invoice_xml = self.invoice.with_context(
            force_report_rendering=True
        ).attach_ubl_xml_file_button()
        att = self.env["ir.attachment"].browse(invoice_xml["res_id"])
        xml_content = base64.b64decode(att.with_context(bin_size=False).datas)

        current_etree = self.get_xml_tree_from_string(xml_content)
        additional_document_elements = current_etree.xpath(
            "//*[local-name()='AdditionalDocumentReference']"
        )
        attach_elements = current_etree.xpath(
            "//*[local-name()='EmbeddedDocumentBinaryObject']"
        )
        if pdf:
            pdf_filename = "%s.pdf" % self.invoice.name
            self.assertTrue(additional_document_elements)
            self.assertEqual(len(attach_elements), 1)
            self.assertEqual(attach_elements[0].attrib["mimeCode"], "application/pdf")
            self.assertEqual(attach_elements[0].attrib["filename"], pdf_filename)
            # self.assertEqual(
            #     attach_elements[0].text, pdf_buffer
            # )
        else:
            self.assertFalse(additional_document_elements)
            self.assertFalse(attach_elements)

    def test_l10n_ro_add_pdf_to_xml_no_pdf(self):
        self.invoice.action_post()
        self.check_xml_pdf_embedded(False)

    def test_l10n_ro_add_pdf_to_xml(self):
        self.invoice.company_id.l10n_ro_edi_cius_embed_pdf = True
        self.invoice.action_post()
        self.check_xml_pdf_embedded(True)

    def test_l10n_ro_add_pdf_to_xml_other_report(self):
        self.invoice.company_id.l10n_ro_edi_cius_embed_pdf = True
        self.invoice.company_id.l10n_ro_default_cius_pdf_report = self.env.ref(
            "account.account_invoices"
        ).id
        self.invoice.action_post()
        self.check_xml_pdf_embedded(True)
