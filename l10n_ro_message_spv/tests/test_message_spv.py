# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import io
import json
import zipfile
from unittest.mock import patch

from lxml import etree

from odoo.tests import tagged
from odoo.tools.misc import file_path

from .common import TestMessageSPV


@tagged("post_install", "-at_install")
class TestMessageSPV(TestMessageSPV):
    # test de creare mesaje preluate de la SPV

    def setUp(self):
        super().setUp()
        self.env.user.lang = "en_US"
        self.vendor = self.env["res.partner"].create(
            {
                "name": "Deltatech",
                "country_id": self.env.ref("base.ro").id,
                "vat": "RO20603502",
                "is_company": True,
            }
        )

    def test_download_messages(self):
        # test de descarcare a mesajelor de la SPV
        self.env.company.vat = "RO23685159"

        msg_dict = {
            "mesaje": [
                {
                    "data_creare": "202312120940",
                    "cif": "23685159",
                    "id_solicitare": "5004552043",
                    "detalii": "Factura cu id_incarcare=5004552043 emisa de cif_emitent=8486152 pentru cif_beneficiar=23685159",  # noqa
                    "tip": "FACTURA PRIMITA",
                    "id": "3006372781",
                },
                {
                    "data_creare": "202312120945",
                    "cif": "23685159",
                    "id_solicitare": "5004552044",
                    "detalii": "Mesaj de test",
                    "tip": "MESAJ",
                    "id": "3006372782",
                },
            ],
            "serial": "1234AA456",
            "cui": "8000000000",
            "titlu": "Lista Mesaje disponibile din ultimele 1 zile",
            "numar_total_pagini": 1,
        }
        anaf_messages = {"content": b"""%s""" % json.dumps(msg_dict).encode("utf-8")}

        with patch(
            "odoo.addons.l10n_ro_message_spv.models.ciusro_document.make_efactura_request",
            return_value=anaf_messages,
        ):
            self.env.company._l10n_ro_download_message_spv()

    def test_download_from_spv_error(self):
        """Testează gestionarea erorilor la descarcare de la SPV"""
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "ERR_DOWN",
                "company_id": self.env.company.id,
            }
        )
        with patch(
            "odoo.addons.l10n_ro_message_spv.models.ciusro_document.make_efactura_request",
            return_value={"error": "Invalid token"},
        ):
            message_spv.download_from_spv()
            self.assertEqual(message_spv.error, "Invalid token")

    def test_download_from_spv(self):
        # test descarcare zip from SPV
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "3006372781",
                "company_id": self.env.company.id,
                "message_type": "in_invoice",
                "cif": "8486152",
            }
        )

        file_invoice = file_path("l10n_ro_message_spv/tests/invoice.zip")
        anaf_messages = {"content": open(file_invoice, "rb").read()}
        with patch(
            "odoo.addons.l10n_ro_message_spv.models.ciusro_document.make_efactura_request",
            return_value=anaf_messages,
        ):
            message_spv.download_from_spv()
        message_spv.get_invoice_from_move()
        message_spv.create_invoice()
        message_spv.show_invoice()

    def test_unlink_account_move(self):
        """Testează funcționalitatea de ștergere a
        facturilor care au mesaje SPV atașate"""
        # Creăm o factură și mesaje SPV atașate
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "3006372781",
                "company_id": self.env.company.id,
                "message_type": "in_invoice",
                "cif": "8486152",
            }
        )

        # Creăm atașamente
        attachment = self.env["ir.attachment"].create(
            {
                "name": "test_attachment",
                "type": "binary",
                "datas": b"dGVzdA==",  # "test" codificat în base64
            }
        )

        # Asociăm atașamentele cu mesajul SPV
        message_spv.write(
            {
                "attachment_id": attachment.id,
            }
        )

        # Creăm o factură și o asociem cu mesajul SPV
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
            }
        )
        message_spv.write({"invoice_id": invoice.id})

        # Verificăm că mesajul SPV este asociat cu factura
        self.assertEqual(invoice.l10n_ro_message_spv_ids[0].id, message_spv.id)

        # Ștergem factura
        invoice.unlink()

        # Verificăm că atașamentul nu mai este asociat cu niciun model/înregistrare
        self.assertFalse(attachment.res_id)
        self.assertFalse(attachment.res_model)

    def test_edi_transaction_tracking(self):
        """Testează câmpurile de urmărire a tranzacțiilor EDI"""
        # Creăm o factură
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
            }
        )

        # Setăm valorile pentru câmpurile de urmărire a tranzacțiilor
        transaction_id = "TR123456789"
        download_id = "DL987654321"

        invoice.write(
            {
                "l10n_ro_edi_transaction": transaction_id,
                "l10n_ro_edi_download": download_id,
            }
        )

        # Verificăm că valorile au fost setate corect
        self.assertEqual(invoice.l10n_ro_edi_transaction, transaction_id)
        self.assertEqual(invoice.l10n_ro_edi_download, download_id)

    def test_vendor_code_on_post(self):
        """Testează adăugarea codului de furnizor la postarea facturii"""
        # Creăm un produs
        product = self.env["product.product"].create(
            {
                "name": "Test Product",
            }
        )

        # Creăm o factură cu linie ce conține codul furnizorului

        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": "2023-12-01",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "name": "Test Line",
                            "quantity": 1,
                            "price_unit": 100,
                            "l10n_ro_vendor_code": "VEND001",
                        },
                    )
                ],
            }
        )

        # Postăm factura
        invoice.action_post()

        # Verificăm că s-a creat o informație de furnizor cu codul corect
        supplier_info = self.env["product.supplierinfo"].search(
            [
                ("partner_id", "=", self.vendor.id),
                ("product_id", "=", product.id),
            ]
        )

        self.assertTrue(supplier_info)
        self.assertEqual(supplier_info.product_code, "VEND001")

    def test_get_xml_from_zip_variants(self):
        """Testează diverse variante de XML în ZIP (CreditNote, Receipt, lipsă date)"""
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "TEST_VARIANTS",
                "message_type": "in_invoice",
                "request_id": "REQ_VARIANTS",
            }
        )

        def create_zip_with_xml(xml_content):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as zip_file:
                zip_file.writestr("test.xml", xml_content)
            return buffer.getvalue()

        # Test CreditNote
        credit_note_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <CreditNote xmlns="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
                    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
            <cbc:ID>CN123</cbc:ID>
            <cbc:IssueDate>2024-01-01</cbc:IssueDate>
            <cbc:DocumentCurrencyCode>RON</cbc:DocumentCurrencyCode>
            <cac:LegalMonetaryTotal>
                <cbc:TaxInclusiveAmount currencyID="RON">100.00</cbc:TaxInclusiveAmount>
            </cac:LegalMonetaryTotal>
        </CreditNote>"""

        attachment = self.env["ir.attachment"].create(
            {
                "name": "test.zip",
                "raw": create_zip_with_xml(credit_note_xml),
            }
        )
        message_spv.attachment_id = attachment
        message_spv.get_xml_fom_zip()
        self.assertEqual(message_spv.amount, -100.0)
        self.assertEqual(message_spv.ref, "CN123")

        # Test Receipt (InvoiceTypeCode 751)
        receipt_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
                 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
            <cbc:InvoiceTypeCode>751</cbc:InvoiceTypeCode>
            <cbc:ID>REC123</cbc:ID>
        </Invoice>"""

        message_spv.message_type = "in_invoice"
        message_spv.attachment_id.raw = create_zip_with_xml(receipt_xml)
        message_spv.get_xml_fom_zip()
        self.assertEqual(message_spv.message_type, "in_receipt")

    def test_anaf_errors_and_messages(self):
        """Testează gestionarea erorilor și mesajelor de la ANAF"""
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "TEST_ERR",
                "request_id": "REQ123",
                "message_type": "message",
            }
        )

        # Test check_anaf_message_xml
        msg_xml = b"""<?xml version="1.0" encoding="UTF-8"?><Message message="Test ANAF Message"/>"""  # noqa
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zip_file:
            zip_file.writestr("REQ123.xml", msg_xml)

        zip_content = buffer.getvalue()
        info_msg = message_spv.check_anaf_message_xml(zip_content)
        self.assertEqual(info_msg, "Test ANAF Message")

        # Test check_anaf_error_xml
        err_xml = b"""<?xml version="1.0" encoding="UTF-8"?> <ErrorResponse><Error errorMessage="Error 1"/> <Error errorMessage="Error 2"/> </ErrorResponse>"""  # noqa
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zip_file:
            zip_file.writestr("REQ123.xml", err_xml)

        zip_content = buffer.getvalue()
        err_msg = message_spv.check_anaf_error_xml(zip_content)
        self.assertIn("Error 1", err_msg)
        self.assertIn("Error 2", err_msg)

    def test_pdf_rendering_and_embedded(self):
        """Testează randarea PDF și extragerea PDF-ului embedded"""
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "TEST_PDF",
                "request_id": "REQ_PDF",
            }
        )
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?><Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"><cbc:ID>INV123</cbc:ID><cac:AdditionalDocumentReference><cbc:ID>embedded.pdf</cbc:ID><cac:Attachment><cbc:EmbeddedDocumentBinaryObject mimeCode="application/pdf">dGVzdA==</cbc:EmbeddedDocumentBinaryObject></cac:Attachment></cac:AdditionalDocumentReference></Invoice>"""  # noqa

        attachment_xml = self.env["ir.attachment"].create(
            {
                "name": "test.xml",
                "raw": xml_content,
            }
        )
        message_spv.attachment_xml_id = attachment_xml
        # attachment_id is required by render_anaf_pdf
        message_spv.attachment_id = attachment_xml

        # Mock requests.post for PDF rendering
        with patch(
            "odoo.addons.l10n_ro_message_spv.models.message_spv.requests.post"
        ) as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.content = b"PDF_CONTENT"
            message_spv.render_anaf_pdf()
            message_spv.invalidate_recordset()
            self.assertTrue(message_spv.attachment_anaf_pdf_id)

            # Test failure and retry with no_validate
            mock_post.return_value.status_code = 400
            mock_post.return_value.text = "Error"
            message_spv.attachment_anaf_pdf_id = False
            # We need to make sure the second call (recursive) also happens
            # but we need to check if it actually sets the field if it fails.
            # In code: if res.status_code != 200 and no_validate
            # is None: self.render_xml_anaf_pdf(no_validate=True)
            message_spv.render_anaf_pdf()
            # If it fails twice, it won't have an attachment
            self.assertFalse(message_spv.attachment_anaf_pdf_id)

        # Test embedded PDF
        message_spv.get_embedded_pdf()
        self.assertTrue(message_spv.attachment_embedded_pdf_id)
        self.assertEqual(message_spv.attachment_embedded_pdf_id.name, "embedded.pdf")

    def test_missing_data_coverage(self):
        """Testează ramurile de date lipsă în get_xml_fom_zip și get_embedded_pdf"""
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "TEST_MISSING",
                "request_id": "REQ_MISSING",
            }
        )
        # 1. get_xml_fom_zip fără attachment
        message_spv.get_xml_fom_zip()
        self.assertFalse(message_spv.attachment_xml_id)

        # 2. get_xml_fom_zip cu ZIP gol
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zip_file:  # noqa
            pass
        attachment = self.env["ir.attachment"].create(
            {"name": "empty.zip", "raw": buffer.getvalue()}
        )
        message_spv.attachment_id = attachment
        message_spv.get_xml_fom_zip()
        self.assertFalse(message_spv.attachment_xml_id)

        # 3. get_embedded_pdf declanșează download_from_spv și get_xml_fom_zip
        message_spv.attachment_id = False
        message_spv.attachment_xml_id = False
        with (
            patch.object(type(message_spv), "download_from_spv") as mock_download,
            patch.object(type(message_spv), "get_xml_fom_zip") as mock_get_xml,
        ):
            # Mock get_xml_fom_zip to set attachment_xml_id so
            # the rest of method doesn't crash
            def side_effect_get_xml():
                message_spv.attachment_xml_id = self.env["ir.attachment"].create(
                    {"name": "test.xml", "raw": b"<root/>"}
                )

            mock_get_xml.side_effect = side_effect_get_xml
            message_spv.get_embedded_pdf()
            self.assertTrue(mock_download.called)
            self.assertTrue(mock_get_xml.called)

    def test_create_invoice_error(self):
        """Testează ramura de eroare în create_invoice"""
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "TEST_CREATE_ERR",
                "message_type": "in_invoice",
                "partner_id": self.vendor.id,
            }
        )
        message_spv.attachment_xml_id = self.env["ir.attachment"].create(
            {"name": "test.xml", "raw": b"<root/>"}
        )

        with patch(
            "odoo.addons.account.models.account_move.AccountMove._extend_with_attachments",
            side_effect=Exception("Test Exception"),
        ):
            message_spv.create_invoice()
            self.assertEqual(message_spv.state, "error")
            self.assertIn("Test Exception", message_spv.error)

    def test_advanced_invoice_matching(self):
        """Testează potrivirea avansată a facturilor (get_invoice_from_move)"""
        partner = self.env["res.partner"].create(
            {"name": "Partner Test", "vat": "RO123", "is_company": True}
        )
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": partner.id,
                "ref": "REF123",
                "invoice_date": "2024-01-01",
                "invoice_line_ids": [
                    (0, 0, {"name": "test", "quantity": 1, "price_unit": 100})
                ],
                "l10n_ro_edi_download": "MSG123",
            }
        )
        invoice.action_post()

        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "MSG123",
                "request_id": "REQ123",
                "cif": "123",
                "ref": "REF123",
                "message_type": "in_invoice",
            }
        )

        # Match by ref and partner
        message_spv.get_invoice_from_move()
        self.assertEqual(message_spv.invoice_id.id, invoice.id)

        # Match for error message
        error_msg_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "ERR123",
                "request_id": "REQ_ERR",
                "message_type": "error",
                "error": "ANAF Error",
            }
        )
        invoice.l10n_ro_edi_index = "REQ_ERR"
        edi_doc = self.env["l10n_ro_edi.document"].create(
            {
                "invoice_id": invoice.id,
                "state": "invoice_sent",
            }
        )

        error_msg_spv.get_invoice_from_move()
        self.assertEqual(error_msg_spv.invoice_id.id, invoice.id)
        self.assertEqual(edi_doc.state, "invoice_refused")

    def test_create_invoice_variants(self):
        """Testează crearea facturii cu gestionarea duplicatelor și erori"""
        partner = self.env["res.partner"].create(
            {"name": "Partner Test", "vat": "RO123", "is_company": True}
        )
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "MSG_CREATE",
                "request_id": "REQ_CREATE",
                "cif": "123",
                "ref": "REF_DUP",
                "message_type": "in_invoice",
                "partner_id": partner.id,
            }
        )

        xml_content = b'<?xml version="1.0" encoding="UTF-8"?><Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"><cbc:ID>REF_DUP</cbc:ID></Invoice>'  # noqa: E501
        attachment_xml = self.env["ir.attachment"].create(
            {
                "name": "test.xml",
                "raw": xml_content,
            }
        )
        message_spv.attachment_xml_id = attachment_xml

        # Create an existing posted invoice
        existing_invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": partner.id,
                "ref": "REF_DUP",
                "invoice_date": "2024-01-01",
                "invoice_line_ids": [
                    (0, 0, {"name": "test", "quantity": 1, "price_unit": 100})
                ],
            }
        )
        existing_invoice.action_post()
        self.assertEqual(existing_invoice.state, "posted")
        self.assertEqual(existing_invoice.commercial_partner_id.id, partner.id)

        # Should match existing instead of creating new
        message_spv.create_invoice()

        # Invalidate cache and flush to ensure everything is in DB
        self.env["account.move"].flush_model()
        existing_invoice.invalidate_recordset()

        self.assertEqual(message_spv.invoice_id.id, existing_invoice.id)

    def test_onchange_invoice_id(self):
        """Testează _onchange_invoice_id pentru diverse tipuri de facturi"""
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": "2024-01-01",
                "invoice_line_ids": [
                    (0, 0, {"name": "test", "quantity": 1, "price_unit": 100})
                ],
            }
        )
        refund = self.env["account.move"].create(
            {
                "move_type": "in_refund",
                "partner_id": self.vendor.id,
                "invoice_date": "2024-01-01",
                "invoice_line_ids": [
                    (0, 0, {"name": "test", "quantity": 1, "price_unit": 50})
                ],
            }
        )

        message = self.env["l10n.ro.message.spv"].create(
            {
                "name": "TEST_ONCHANGE",
                "invoice_id": invoice.id,
            }
        )
        message._onchange_invoice_id()
        self.assertEqual(message.invoice_amount, 100.0)

        message.invoice_id = refund
        message._onchange_invoice_id()
        self.assertEqual(message.invoice_amount, -50.0)

    def test_utility_methods_and_actions(self):
        """Testează metodele de utilitate
        (get_partner, refresh, show_invoice, download)"""
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "MSG_UTIL",
                "cif": "RO999",
            }
        )

        # get_partner
        message_spv.get_partner()
        self.assertTrue(message_spv.partner_id)
        self.assertEqual(message_spv.partner_id.vat, "RO999")

        # show_invoice
        invoice = self.env["account.move"].create(
            {"move_type": "in_invoice", "partner_id": message_spv.partner_id.id}
        )
        message_spv.invoice_id = invoice
        action = message_spv.show_invoice()
        self.assertEqual(action["res_model"], "account.move")

        # download actions
        attachment = self.env["ir.attachment"].create({"name": "test", "raw": b"test"})
        message_spv.attachment_id = attachment
        res = message_spv.action_download_attachment()
        self.assertIn(str(attachment.id), res["url"])

        attachment_xml = self.env["ir.attachment"].create(
            {"name": "test.xml", "raw": b"test"}
        )
        message_spv.attachment_xml_id = attachment_xml
        res = message_spv.action_download_xml()
        self.assertIn(str(attachment_xml.id), res["url"])

        attachment_pdf = self.env["ir.attachment"].create(
            {"name": "test.pdf", "raw": b"test", "type": "binary"}
        )
        message_spv.attachment_anaf_pdf_id = attachment_pdf
        res = message_spv.action_download_anaf_pdf()
        self.assertIn(str(attachment_pdf.id), res["url"])

        attachment_emb = self.env["ir.attachment"].create(
            {"name": "test_emb.pdf", "raw": b"test", "type": "binary"}
        )
        message_spv.attachment_embedded_pdf_id = attachment_emb
        res = message_spv.action_download_embedded_pdf()
        self.assertIn(str(attachment_emb.id), res["url"])

        # refresh
        with patch(
            "odoo.addons.l10n_ro_message_spv.models.res_company.ResCompany._l10n_ro_download_message_spv"  # noqa
        ) as mock_download:
            message_spv.refresh()
            self.assertTrue(mock_download.called)

    def test_cron_methods(self):
        """Testează metodele apelate de cron jobs pe res.company"""
        self.env.company.l10n_ro_edi_access_token = "123"
        self.env.company.vat = "RO23685159"

        # 1. Test l10n_ro_download_message_spv
        msg_dict = {
            "mesaje": [
                {
                    "data_creare": "202312120940",
                    "cif": "23685159",
                    "id_solicitare": "CRON_REQ_1",
                    "detalii": "Factura emisa de 8486152",
                    "tip": "FACTURA PRIMITA",
                    "id": "CRON_MSG_1",
                }
            ],
            "numar_total_pagini": 1,
        }
        anaf_messages = {"content": json.dumps(msg_dict).encode("utf-8")}

        with patch(
            "odoo.addons.l10n_ro_message_spv.models.ciusro_document.make_efactura_request",
            return_value=anaf_messages,
        ):
            self.env.company.l10n_ro_download_message_spv()

        # Verificăm că mesajul a fost creat
        msg = self.env["l10n.ro.message.spv"].search([("name", "=", "CRON_MSG_1")])
        self.assertTrue(msg)
        self.assertEqual(msg.request_id, "CRON_REQ_1")

        # 2. Test l10n_ro_download_zip_message_spv
        # Mocking zip download
        file_invoice = file_path("l10n_ro_message_spv/tests/invoice.zip")
        zip_content = {"content": open(file_invoice, "rb").read()}

        with patch(
            "odoo.addons.l10n_ro_message_spv.models.ciusro_document.make_efactura_request",
            return_value=zip_content,
        ):
            # Limităm la 5 mesaje, oricum avem doar unul creat acum fără atașament
            self.env.company.l10n_ro_download_zip_message_spv(limit=5)

        # Verificăm că atașamentul a fost descărcat
        self.assertTrue(msg.attachment_id)
        self.assertEqual(msg.state, "downloaded")

    def test_import_fill_invoice_line_form(self):
        """Testează _import_fill_invoice_line_form
        pentru extragerea codului furnizor și potrivirea produsului"""
        # 1. Creăm un produs cu supplierinfo (seller_ids)
        product = self.env["product.product"].create(
            {
                "name": "Import Test Product",
            }
        )
        self.env["product.supplierinfo"].create(
            {
                "partner_id": self.vendor.id,
                "product_tmpl_id": product.product_tmpl_id.id,
                "product_code": "VEND_IMPORT_001",
            }
        )

        # 2. Pregătim un XML minimal care să conțină SellersItemIdentification
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1</cbc:CustomizationID>
    <cbc:ID>INV_IMPORT_001</cbc:ID>
    <cac:InvoiceLine>
        <cbc:ID>1</cbc:ID>
        <cbc:InvoicedQuantity>1.0</cbc:InvoicedQuantity>
        <cbc:LineExtensionAmount currencyID="RON">100.0</cbc:LineExtensionAmount>
        <cac:Item>
            <cbc:Name>Import Test Product</cbc:Name>
            <cac:SellersItemIdentification>
                <cbc:ID>VEND_IMPORT_001</cbc:ID>
            </cac:SellersItemIdentification>
        </cac:Item>
        <cac:Price>
            <cbc:PriceAmount currencyID="RON">100.0</cbc:PriceAmount>
        </cac:Price>
    </cac:InvoiceLine>
</Invoice>"""

        attachment_xml = self.env["ir.attachment"].create(
            {
                "name": "import_test.xml",
                "raw": xml_content,
                "mimetype": "application/xml",
            }
        )

        # 3. Creăm o factură și apelăm importul
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
            }
        )

        # Pregătim datele fișierului așa cum le așteaptă Odoo 19
        file_data = {
            "attachment": attachment_xml,
            "name": attachment_xml.name,
            "filename": attachment_xml.name,
            "content": attachment_xml.raw,
            "mimetype": attachment_xml.mimetype,
            "type": "xml",
            "xml_tree": etree.fromstring(attachment_xml.raw),
        }
        # Identificăm tipul de fișier pentru a activa decoderul corect
        file_data["import_file_type"] = invoice._get_import_file_type(file_data)

        # Metoda _extend_with_attachments apelează intern logica de import UBL
        invoice._extend_with_attachments([file_data])

        # 4. Verificăm rezultatele pe prima linie a facturii
        line = invoice.invoice_line_ids[0]
        self.assertEqual(line.l10n_ro_vendor_code, "VEND_IMPORT_001")
        self.assertEqual(line.product_id.id, product.id)

        # 5. Testăm și cu StandardItemIdentification
        xml_content_std = xml_content.replace(
            b"SellersItemIdentification", b"StandardItemIdentification"
        )
        attachment_xml_std = self.env["ir.attachment"].create(
            {
                "name": "import_test_std.xml",
                "raw": xml_content_std,
                "mimetype": "application/xml",
            }
        )
        invoice_std = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
            }
        )
        file_data_std = {
            "attachment": attachment_xml_std,
            "name": attachment_xml_std.name,
            "filename": attachment_xml_std.name,
            "content": attachment_xml_std.raw,
            "mimetype": attachment_xml_std.mimetype,
            "type": "xml",
            "xml_tree": etree.fromstring(attachment_xml_std.raw),
        }
        file_data_std["import_file_type"] = invoice_std._get_import_file_type(
            file_data_std
        )

        invoice_std._extend_with_attachments([file_data_std])
        line_std = invoice_std.invoice_line_ids[0]
        self.assertEqual(line_std.l10n_ro_vendor_code, "VEND_IMPORT_001")
        self.assertEqual(line_std.product_id.id, product.id)
