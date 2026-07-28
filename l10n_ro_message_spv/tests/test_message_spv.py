# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import io
import json
import zipfile
from unittest.mock import MagicMock, patch

from dateutil.relativedelta import relativedelta
from lxml import etree

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import Form, tagged
from odoo.tools.misc import file_path

from .common import TestMessageSPV

EMBEDDED_PDF_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:ID>TESTEMB</cbc:ID>
    <cac:AdditionalDocumentReference>
        <cbc:ID>embedded.pdf</cbc:ID>
        <cac:Attachment>
            <cbc:EmbeddedDocumentBinaryObject
                mimeCode="application/pdf"
            >JVBERi10ZXN0</cbc:EmbeddedDocumentBinaryObject>
        </cac:Attachment>
    </cac:AdditionalDocumentReference>
</Invoice>
"""


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

    def _create_message_with_zip(self, name, request_id, xml_bytes, **extra):
        """Create a message holding a ZIP built in memory around xml_bytes."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zip_file:
            zip_file.writestr(f"{request_id}.xml", xml_bytes)
            zip_file.writestr(f"semnatura_{request_id}.xml", b"<signature/>")
        values = {
            "name": name,
            "request_id": request_id,
            "company_id": self.env.company.id,
            "message_type": "in_invoice",
        }
        values.update(extra)
        message = self.env["l10n.ro.message.spv"].create(values)
        attachment = self.env["ir.attachment"].create(
            {
                "name": f"{request_id}.zip",
                "raw": buffer.getvalue(),
                "mimetype": "application/zip",
            }
        )
        message.write({"attachment_id": attachment.id, "state": "downloaded"})
        return message

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

    def test_download_attempts_limit(self):
        """Testează limitarea la 3 încercări de descărcare și trecerea
        în starea de eroare"""
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "TEST_LIMIT",
                "company_id": self.env.company.id,
                "message_type": "in_invoice",
            }
        )

        # Simulăm un răspuns cu eroare de la ANAF
        error_response = {"error": "Limita de descărcări atinsă"}

        with patch(
            "odoo.addons.l10n_ro_message_spv.models.ciusro_document.make_efactura_request",
            return_value=error_response,
        ):
            # Prima încercare
            message_spv.download_from_spv()
            self.assertEqual(message_spv.download_attempts, 1)
            self.assertEqual(message_spv.state, "draft")

            # A doua încercare
            message_spv.download_from_spv()
            self.assertEqual(message_spv.download_attempts, 2)
            self.assertEqual(message_spv.state, "draft")

            # A treia încercare -> starea devine eroare
            message_spv.download_from_spv()
            self.assertEqual(message_spv.download_attempts, 3)
            self.assertEqual(message_spv.state, "error")

    def test_download_attempts_daily_reset(self):
        """Testează resetarea încercărilor de descărcare la schimbarea zilei"""
        yesterday = fields.Date.today() - relativedelta(days=1)
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "TEST_RESET",
                "company_id": self.env.company.id,
                "message_type": "in_invoice",
                "download_attempts": 2,
                "last_download_date": yesterday,
            }
        )

        # Simulăm un răspuns cu eroare
        error_response = {"error": "Eroare temporară"}

        with patch(
            "odoo.addons.l10n_ro_message_spv.models.ciusro_document.make_efactura_request",
            return_value=error_response,
        ):
            # Descărcarea astăzi ar trebui să reseteze încercările la 1
            message_spv.download_from_spv()
            self.assertEqual(message_spv.download_attempts, 1)
            self.assertEqual(message_spv.last_download_date, fields.Date.today())

    def test_cron_error_persistence_with_rollback(self):
        """Testează dacă download_attempts este salvat de cron chiar
        și în caz de excepție Python"""
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "TEST_ROLLBACK",
                "company_id": self.env.company.id,
                "state": "draft",
                "download_attempts": 0,
            }
        )

        # Forțăm o excepție în timpul download_from_spv pentru a verifica
        # că eroarea este capturată și persistată de cron.
        with self.assertLogs(
            "odoo.addons.l10n_ro_message_spv.models.res_company", level="ERROR"
        ) as cm:
            with patch.object(
                type(self.env["l10n.ro.message.spv"]),
                "download_from_spv",
                side_effect=Exception("Crash!"),
            ):
                self.env.company.l10n_ro_download_zip_message_spv(limit=1)

            self.assertTrue(
                any("Eroare la descărcarea ZIP" in log for log in cm.output)
            )

        # În ciuda crash-ului, cron-ul a salvat eroarea și a incrementat încercările
        message_spv.invalidate_recordset()
        self.assertEqual(message_spv.state, "error")
        self.assertEqual(message_spv.download_attempts, 1)
        self.assertIn("Crash!", message_spv.error)

    def test_cron_daily_reset_error_to_draft(self):
        """Testează resetul zilnic error→draft din cron pentru mesajele
        căzute în eroare în zilele trecute"""
        yesterday = fields.Date.today() - relativedelta(days=1)
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "TEST_DAILY_RESET",
                "company_id": self.env.company.id,
                "message_type": "in_invoice",
                "state": "error",
                "download_attempts": 3,
                "last_download_date": yesterday,
            }
        )

        file_invoice = file_path("l10n_ro_message_spv/tests/invoice.zip")
        zip_content = {"content": open(file_invoice, "rb").read()}
        with patch(
            "odoo.addons.l10n_ro_message_spv.models.ciusro_document.make_efactura_request",
            return_value=zip_content,
        ):
            self.env.company.l10n_ro_download_zip_message_spv(limit=5)

        # Mesajul a fost readus în coadă, descărcat și contorul reluat de la 1
        self.assertEqual(message_spv.state, "downloaded")
        self.assertTrue(message_spv.attachment_id)
        self.assertEqual(message_spv.download_attempts, 1)

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

    def test_download_stores_only_zip(self):
        """The download must store only the ZIP; the metadata is parsed in
        memory and no XML attachment is created."""
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "3006372781",
                "request_id": "5004111924",
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

        # only the ZIP is stored
        self.assertTrue(message_spv.attachment_id)
        self.assertEqual(message_spv.attachment_id.mimetype, "application/zip")
        self.assertFalse(message_spv.attachment_xml_id)
        no_xml_attachment = self.env["ir.attachment"].search(
            [("name", "=", "5004111924.xml")]
        )
        self.assertFalse(no_xml_attachment)

        # the metadata was parsed in memory from the ZIP
        self.assertTrue(message_spv.ref)
        self.assertTrue(message_spv.amount)
        self.assertTrue(message_spv.invoice_date)

        # the XML can be derived from the ZIP at any time
        file_name, xml_bytes = message_spv._get_xml_bytes()
        self.assertEqual(file_name, "5004111924.xml")
        self.assertIn(b"Invoice", xml_bytes)

    def test_create_invoice_materializes_xml_on_move(self):
        """create_invoice stores the XML once, directly on the bill, and
        the computed attachment_xml_id finds it there."""
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "3006372781",
                "request_id": "5004111924",
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

        message_spv.create_invoice()

        invoice = message_spv.invoice_id
        self.assertTrue(invoice)
        # the UBL import moves the XML into the invoice's ubl_cii_xml_file
        # binary field — a single stored copy, on the bill
        xml_attachment = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "account.move"),
                ("res_id", "=", invoice.id),
                ("res_field", "in", ["ubl_cii_xml_file", False]),
                ("name", "=", "5004111924.xml"),
            ]
        )
        self.assertEqual(len(xml_attachment), 1)
        self.assertEqual(message_spv.attachment_xml_id, xml_attachment)

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

        # Facturile primite din SPV primesc un l10n_ro_edi.document (vezi
        # message_spv._confirm). invoice_id e required => ondelete restrict, deci
        # documentul ar bloca stergerea facturii daca nu l-am curata in unlink.
        edi_document = self.env["l10n_ro_edi.document"].create(
            {
                "invoice_id": invoice.id,
                "state": "invoice_validated",
            }
        )

        # Verificăm că mesajul SPV este asociat cu factura
        self.assertEqual(invoice.l10n_ro_message_spv_ids[0].id, message_spv.id)
        self.assertEqual(invoice.l10n_ro_edi_document_ids[0].id, edi_document.id)

        # Ștergem factura (nu trebuie să fie blocată de documentul EDI)
        invoice.unlink()

        # Documentul EDI sintetic a fost curățat odată cu factura
        self.assertFalse(edi_document.exists())

        # Verificăm că atașamentul nu mai este asociat cu niciun model/înregistrare
        self.assertFalse(attachment.res_id)
        self.assertFalse(attachment.res_model)

    def test_unlink_cancelled_spv_bill(self):
        """Factura de achiziție anulată adusă din SPV (cazul raportat) se poate
        șterge chiar dacă are document EDI atașat."""
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "3006372782",
                "company_id": self.env.company.id,
                "message_type": "in_invoice",
                "cif": "8486152",
            }
        )
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
            }
        )
        invoice.button_cancel()
        self.assertEqual(invoice.state, "cancel")
        message_spv.write({"invoice_id": invoice.id})
        edi_document = self.env["l10n_ro_edi.document"].create(
            {"invoice_id": invoice.id, "state": "invoice_validated"}
        )

        invoice.unlink()

        self.assertFalse(edi_document.exists())

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
        """The ANAF PDF and the embedded PDF are derived on the fly from
        the stored ZIP — nothing is persisted."""
        message_spv = self._create_message_with_zip(
            "TEST_PDF", "REQ_PDF", EMBEDDED_PDF_XML
        )

        # Mock requests.post for PDF rendering
        response_ok = MagicMock(status_code=200, content=b"PDF_CONTENT", text="ok")
        with patch(
            "odoo.addons.l10n_ro_message_spv.models.message_spv.requests.post",
            return_value=response_ok,
        ) as mock_post:
            pdf_bytes = message_spv._render_anaf_pdf_bytes()
        self.assertEqual(pdf_bytes, b"PDF_CONTENT")
        self.assertEqual(mock_post.call_count, 1)
        # nothing is stored
        self.assertFalse(message_spv.attachment_anaf_pdf_id)
        self.assertFalse(
            self.env["ir.attachment"].search([("name", "=", "REQ_PDF.pdf")])
        )

        # first attempt fails, the no-validate fallback succeeds
        response_ko = MagicMock(status_code=400, content=b"", text="Error")
        with patch(
            "odoo.addons.l10n_ro_message_spv.models.message_spv.requests.post",
            side_effect=[response_ko, response_ok],
        ) as mock_post:
            pdf_bytes = message_spv._render_anaf_pdf_bytes()
        self.assertEqual(pdf_bytes, b"PDF_CONTENT")
        self.assertEqual(mock_post.call_count, 2)

        # both attempts fail
        with patch(
            "odoo.addons.l10n_ro_message_spv.models.message_spv.requests.post",
            return_value=response_ko,
        ):
            with self.assertRaises(UserError):
                message_spv._render_anaf_pdf_bytes()

        # the ANAF WAF rejects the request
        response_waf = MagicMock(
            status_code=200, content=b"", text="The requested URL was rejected"
        )
        with patch(
            "odoo.addons.l10n_ro_message_spv.models.message_spv.requests.post",
            return_value=response_waf,
        ):
            with self.assertRaises(UserError):
                message_spv._render_anaf_pdf_bytes()

        # the embedded PDF is extracted in memory
        name, pdf_bytes = message_spv._get_embedded_pdf_bytes()
        self.assertEqual(name, "embedded.pdf")
        self.assertEqual(pdf_bytes, b"%PDF-test")
        self.assertFalse(message_spv.attachment_embedded_pdf_id)

        # the download action points to the on-the-fly controller route
        action = message_spv.action_download_embedded_pdf()
        self.assertEqual(
            action["url"], f"/l10n_ro/message_spv/{message_spv.id}/embedded_pdf"
        )

    def test_missing_data_coverage(self):
        """Testează ramurile de date lipsă în derivarea din ZIP"""
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "TEST_MISSING",
                "request_id": "REQ_MISSING",
            }
        )
        # 1. no attachment at all
        message_spv.get_xml_fom_zip()
        self.assertEqual(message_spv._get_xml_bytes(), (False, False))
        self.assertEqual(message_spv._get_embedded_pdf_bytes(), (False, False))
        with self.assertRaises(UserError):
            message_spv._render_anaf_pdf_bytes()

        # 2. empty ZIP
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zip_file:  # noqa
            pass
        attachment = self.env["ir.attachment"].create(
            {"name": "empty.zip", "raw": buffer.getvalue()}
        )
        message_spv.attachment_id = attachment
        message_spv.get_xml_fom_zip()
        self.assertEqual(message_spv._get_xml_bytes(), (False, False))

        # 3. corrupt ZIP
        attachment.raw = b"this is not a zip"
        self.assertEqual(message_spv._get_xml_bytes(), (False, False))

        # 4. XML without an embedded PDF
        message_no_pdf = self._create_message_with_zip(
            "TEST_NOPDF", "REQ_NOPDF", b"<Invoice/>"
        )
        self.assertEqual(message_no_pdf._get_embedded_pdf_bytes(), (False, False))

    def test_create_invoice_error(self):
        """Testează ramura de eroare în create_invoice"""
        message_spv = self._create_message_with_zip(
            "TEST_CREATE_ERR",
            "REQ_CREATE_ERR",
            b"<root/>",
            partner_id=self.vendor.id,
        )

        with patch(
            "odoo.addons.account.models.account_move.AccountMove._extend_with_attachments",
            side_effect=Exception("Test Exception"),
        ):
            message_spv.create_invoice()
            self.assertEqual(message_spv.state, "error")
            self.assertIn("Test Exception", message_spv.error)

        # without a usable ZIP, create_invoice records an error
        message_no_zip = self.env["l10n.ro.message.spv"].create(
            {
                "name": "TEST_CREATE_NOZIP",
                "request_id": "REQ_CREATE_NOZIP",
                "message_type": "in_invoice",
                "partner_id": self.vendor.id,
            }
        )
        message_no_zip.create_invoice()
        self.assertEqual(message_no_zip.state, "error")
        self.assertIn("No XML", message_no_zip.error)

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
        xml_content = b'<?xml version="1.0" encoding="UTF-8"?><Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"><cbc:ID>REF_DUP</cbc:ID></Invoice>'  # noqa: E501
        message_spv = self._create_message_with_zip(
            "MSG_CREATE",
            "REQ_CREATE",
            xml_content,
            cif="123",
            ref="REF_DUP",
            partner_id=partner.id,
        )

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

    def test_received_invoice_edi_state_validated(self):
        """Documentul EDI creat pentru o factură primită trebuie să fie
        invoice_validated, nu invoice_sent.

        Core-ul l10n_ro_edi deduplică facturile primite după
        l10n_ro_edi_state == 'invoice_validated'; dacă punem invoice_sent,
        factura importată nu mai e recunoscută la dedup și cronul o recreează
        (sursa facturilor duplicate)."""
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
            }
        )
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "MSG_VALIDATED",
                "request_id": "REQ_VALIDATED",
                "cif": "123",
                "message_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_id": invoice.id,
            }
        )

        # Nu există încă document EDI pe factură
        self.assertFalse(invoice.l10n_ro_edi_document_ids)

        message_spv.get_data_from_invoice()

        self.assertTrue(invoice.l10n_ro_edi_document_ids)
        self.assertEqual(invoice.l10n_ro_edi_document_ids[0].state, "invoice_validated")
        self.assertEqual(invoice.l10n_ro_edi_state, "invoice_validated")

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

        # download actions: the ZIP is a stored attachment, the derived
        # files are streamed through the controller routes
        attachment = self.env["ir.attachment"].create({"name": "test", "raw": b"test"})
        message_spv.attachment_id = attachment
        res = message_spv.action_download_attachment()
        self.assertIn(str(attachment.id), res["url"])

        res = message_spv.action_download_xml()
        self.assertEqual(res["url"], f"/l10n_ro/message_spv/{message_spv.id}/xml")

        res = message_spv.action_download_anaf_pdf()
        self.assertEqual(res["url"], f"/l10n_ro/message_spv/{message_spv.id}/anaf_pdf")

        # the ZIP holds no embedded PDF: clicking the button must raise a
        # user-friendly error instead of hitting a raw 404
        with self.assertRaises(UserError):
            message_spv.action_download_embedded_pdf()

        # once the files exist on the invoice, the computed fields point to
        # them and the download uses /web/content
        attachment_xml = self.env["ir.attachment"].create(
            {
                "name": "MSG_UTIL_REQ.xml",
                "raw": b"<Invoice/>",
                "res_model": "account.move",
                "res_id": invoice.id,
            }
        )
        message_spv.request_id = "MSG_UTIL_REQ"
        message_spv.invalidate_recordset()
        res = message_spv.action_download_xml()
        self.assertIn(str(attachment_xml.id), res["url"])

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

    def _import_spv_bill_with_one_line(self, spv_marker=None):
        """Bill imported from an SPV XML, holding a single product line.

        `spv_marker` tells which SPV stack created the bill: this module
        (`l10n_ro_edi_download`) or the standard SPV fetch of `l10n_ro_edi`
        (`l10n_ro_edi_index`).
        """
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1</cbc:CustomizationID>
    <cbc:ID>INV_KEEP_001</cbc:ID>
    <cac:InvoiceLine>
        <cbc:ID>1</cbc:ID>
        <cbc:InvoicedQuantity>2.0</cbc:InvoicedQuantity>
        <cbc:LineExtensionAmount currencyID="RON">246.9</cbc:LineExtensionAmount>
        <cac:Item>
            <cbc:Name>Descriere din SPV</cbc:Name>
            <cac:SellersItemIdentification>
                <cbc:ID>VEND_KEEP_001</cbc:ID>
            </cac:SellersItemIdentification>
        </cac:Item>
        <cac:Price>
            <cbc:PriceAmount currencyID="RON">123.45</cbc:PriceAmount>
        </cac:Price>
    </cac:InvoiceLine>
</Invoice>"""
        attachment = self.env["ir.attachment"].create(
            {
                "name": "keep_spv_values.xml",
                "raw": xml_content,
                "mimetype": "application/xml",
            }
        )
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                # marks the bill as coming from SPV
                **(spv_marker or {"l10n_ro_edi_download": "3001"}),
            }
        )
        file_data = {
            "attachment": attachment,
            "name": attachment.name,
            "filename": attachment.name,
            "content": attachment.raw,
            "mimetype": attachment.mimetype,
            "type": "xml",
            "xml_tree": etree.fromstring(attachment.raw),
        }
        file_data["import_file_type"] = invoice._get_import_file_type(file_data)
        invoice._extend_with_attachments([file_data])
        return invoice

    def test_correct_product_keeps_spv_price_and_description(self):
        """Correcting the product on an SPV line keeps the imported
        description and unit price."""
        invoice = self._import_spv_bill_with_one_line()
        line = invoice.invoice_line_ids[0]
        spv_name = line.name
        self.assertIn("Descriere din SPV", spv_name)
        self.assertEqual(line.price_unit, 123.45)
        self.assertTrue(line._l10n_ro_is_spv_imported_line())

        correct_product = self.env["product.product"].create(
            {
                "name": "Produsul corect",
                "description_purchase": "Descriere din fisa produsului",
                "standard_price": 10.0,
                "list_price": 10.0,
            }
        )
        line.product_id = correct_product

        self.assertEqual(line.product_id, correct_product)
        self.assertEqual(line.name, spv_name)
        self.assertEqual(line.price_unit, 123.45)

    def test_correct_product_keeps_spv_values_on_core_imported_bill(self):
        """Same protection on bills created by the standard `l10n_ro_edi`
        SPV fetch, which marks them with `l10n_ro_edi_index`."""
        invoice = self._import_spv_bill_with_one_line(
            spv_marker={"l10n_ro_edi_index": "3002"}
        )
        line = invoice.invoice_line_ids[0]
        spv_name = line.name
        self.assertTrue(line._l10n_ro_is_spv_imported_line())

        correct_product = self.env["product.product"].create(
            {"name": "Alt produs corect", "standard_price": 7.0}
        )
        line.product_id = correct_product

        self.assertEqual(line.name, spv_name)
        self.assertEqual(line.price_unit, 123.45)

    def test_correct_product_in_form_keeps_spv_price_and_description(self):
        """Same protection through the form onchange, the way the user
        actually corrects the product."""
        invoice = self._import_spv_bill_with_one_line()
        spv_name = invoice.invoice_line_ids[0].name
        correct_product = self.env["product.product"].create(
            {
                "name": "Produsul corect din form",
                "description_purchase": "Descriere din fisa produsului",
                "standard_price": 10.0,
                "list_price": 10.0,
            }
        )

        with Form(invoice) as invoice_form:
            with invoice_form.invoice_line_ids.edit(0) as line_form:
                line_form.product_id = correct_product
                # values seen by the user before saving
                self.assertEqual(line_form.name, spv_name)
                self.assertEqual(line_form.price_unit, 123.45)

        line = invoice.invoice_line_ids[0]
        self.assertEqual(line.product_id, correct_product)
        self.assertEqual(line.name, spv_name)
        self.assertEqual(line.price_unit, 123.45)

    def test_manual_line_on_spv_bill_keeps_standard_behaviour(self):
        """A line keyed in by hand on an SPV bill is filled in from the
        product, as usual."""
        invoice = self._import_spv_bill_with_one_line()
        product = self.env["product.product"].create(
            {
                "name": "Produs adaugat manual",
                "standard_price": 55.0,
            }
        )
        invoice.write(
            {"invoice_line_ids": [(0, 0, {"product_id": product.id, "quantity": 1})]}
        )
        manual_line = invoice.invoice_line_ids.filtered(
            lambda line: line.product_id == product
        )
        self.assertFalse(manual_line._l10n_ro_is_spv_imported_line())
        self.assertEqual(manual_line.name, "Produs adaugat manual")
        self.assertEqual(manual_line.price_unit, 55.0)
