# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import io
import json
import zipfile
from unittest.mock import MagicMock, patch

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tools.misc import file_path

from .common import TestMessageSPV

EMBEDDED_PDF_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:ID>TESTEMB</cbc:ID>
    <cac:AdditionalDocumentReference>
        <cbc:ID>factura.pdf</cbc:ID>
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
                }
            ],
            "serial": "1234AA456",
            "cui": "8000000000",
            "titlu": "Lista Mesaje disponibile din ultimele 1 zile",
        }
        anaf_messages = {"content": b"""%s""" % json.dumps(msg_dict).encode("utf-8")}

        with patch(
            "odoo.addons.l10n_ro_edi.models.ciusro_document.make_efactura_request",
            return_value=anaf_messages,
        ):
            self.env.company._l10n_ro_download_message_spv()

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
            "odoo.addons.l10n_ro_edi.models.ciusro_document.make_efactura_request",
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
            "odoo.addons.l10n_ro_edi.models.ciusro_document.make_efactura_request",
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

    def test_get_xml_bytes_from_zip(self):
        """The XML is derived in memory from the stored ZIP."""
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "3006372781",
                "request_id": "5004111924",
                "company_id": self.env.company.id,
                "message_type": "in_invoice",
                "cif": "8486152",
            }
        )
        self.assertEqual(message_spv._get_xml_bytes(), (False, False))

        file_invoice = file_path("l10n_ro_message_spv/tests/invoice.zip")
        anaf_messages = {"content": open(file_invoice, "rb").read()}
        with patch(
            "odoo.addons.l10n_ro_edi.models.ciusro_document.make_efactura_request",
            return_value=anaf_messages,
        ):
            message_spv.download_from_spv()

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
            "odoo.addons.l10n_ro_edi.models.ciusro_document.make_efactura_request",
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

    def _create_message_with_zip(self, name, request_id, xml_bytes):
        """Create a message holding a ZIP built in memory around xml_bytes."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zip_file:
            zip_file.writestr(f"{request_id}.xml", xml_bytes)
            zip_file.writestr(f"semnatura_{request_id}.xml", b"<signature/>")
        message = self.env["l10n.ro.message.spv"].create(
            {
                "name": name,
                "request_id": request_id,
                "company_id": self.env.company.id,
                "message_type": "in_invoice",
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": f"{request_id}.zip",
                "raw": buf.getvalue(),
                "mimetype": "application/zip",
            }
        )
        message.write({"attachment_id": attachment.id, "state": "downloaded"})
        return message

    def test_embedded_pdf_from_zip(self):
        """The embedded PDF is derived in memory from the ZIP."""
        message = self._create_message_with_zip("EMB1", "TESTEMB", EMBEDDED_PDF_XML)
        name, pdf_bytes = message._get_embedded_pdf_bytes()
        self.assertEqual(name, "factura.pdf")
        self.assertEqual(pdf_bytes, b"%PDF-test")

    def test_embedded_pdf_absent(self):
        """XML without an embedded PDF yields nothing."""
        message = self._create_message_with_zip("EMB2", "TESTNOPDF", b"<Invoice/>")
        name, pdf_bytes = message._get_embedded_pdf_bytes()
        self.assertFalse(name)
        self.assertFalse(pdf_bytes)

    def test_get_xml_bytes_bad_zip(self):
        """A corrupt ZIP is handled gracefully."""
        message = self.env["l10n.ro.message.spv"].create(
            {
                "name": "BADZIP",
                "request_id": "BADZIP",
                "company_id": self.env.company.id,
                "message_type": "in_invoice",
            }
        )
        attachment = self.env["ir.attachment"].create(
            {"name": "bad.zip", "raw": b"this is not a zip"}
        )
        message.write({"attachment_id": attachment.id})
        self.assertEqual(message._get_xml_bytes(), (False, False))

    def test_render_anaf_pdf_bytes(self):
        """The ANAF PDF is rendered on the fly and never stored."""
        message = self._create_message_with_zip("ANAF1", "TESTANAF", b"<Invoice/>")

        # successful conversion
        response_ok = MagicMock(status_code=200, content=b"%PDF-anaf", text="ok")
        with patch(
            "odoo.addons.l10n_ro_message_spv.models.message_spv.requests.post",
            return_value=response_ok,
        ) as post:
            pdf_bytes = message._render_anaf_pdf_bytes()
        self.assertEqual(pdf_bytes, b"%PDF-anaf")
        self.assertEqual(post.call_count, 1)
        self.assertFalse(
            self.env["ir.attachment"].search([("name", "=", "TESTANAF.pdf")])
        )

        # first attempt fails with a validation error, the no-validate
        # fallback succeeds
        response_ko = MagicMock(status_code=400, content=b"", text="invalid")
        with patch(
            "odoo.addons.l10n_ro_message_spv.models.message_spv.requests.post",
            side_effect=[response_ko, response_ok],
        ) as post:
            pdf_bytes = message._render_anaf_pdf_bytes()
        self.assertEqual(pdf_bytes, b"%PDF-anaf")
        self.assertEqual(post.call_count, 2)

        # the ANAF WAF rejects the request
        response_waf = MagicMock(
            status_code=200, content=b"", text="The requested URL was rejected"
        )
        with patch(
            "odoo.addons.l10n_ro_message_spv.models.message_spv.requests.post",
            return_value=response_waf,
        ):
            with self.assertRaises(UserError):
                message._render_anaf_pdf_bytes()

        # no ZIP at all
        message_no_zip = self.env["l10n.ro.message.spv"].create(
            {
                "name": "ANAF2",
                "request_id": "TESTANAF2",
                "company_id": self.env.company.id,
                "message_type": "in_invoice",
            }
        )
        with self.assertRaises(UserError):
            message_no_zip._render_anaf_pdf_bytes()

    def test_action_download_urls(self):
        """Without an invoice the download actions point to the on-the-fly
        controller routes; the ZIP one downloads the stored attachment."""
        message = self._create_message_with_zip("DL1", "TESTDL", b"<Invoice/>")
        action = message.action_download_attachment()
        self.assertEqual(
            action["url"], f"/web/content/{message.attachment_id.id}?download=true"
        )
        action = message.action_download_xml()
        self.assertEqual(action["url"], f"/l10n_ro/message_spv/{message.id}/xml")
        action = message.action_download_anaf_pdf()
        self.assertEqual(action["url"], f"/l10n_ro/message_spv/{message.id}/anaf_pdf")

    def test_action_download_embedded_pdf_url(self):
        """When the XML holds an embedded PDF, the action points to the
        on-the-fly controller route."""
        message = self._create_message_with_zip("DL2", "TESTDL2", EMBEDDED_PDF_XML)
        action = message.action_download_embedded_pdf()
        self.assertEqual(
            action["url"], f"/l10n_ro/message_spv/{message.id}/embedded_pdf"
        )

    def test_action_download_embedded_pdf_missing_raises(self):
        """Clicking the button when the XML has no embedded PDF must raise
        a user-friendly error instead of surfacing a raw 404."""
        message = self._create_message_with_zip("DL3", "TESTDL3", b"<Invoice/>")
        with self.assertRaises(UserError):
            message.action_download_embedded_pdf()

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
            "odoo.addons.l10n_ro_edi.models.ciusro_document.make_efactura_request",
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
            "odoo.addons.l10n_ro_edi.models.ciusro_document.make_efactura_request",
            return_value=error_response,
        ):
            # Descărcarea astăzi ar trebui să reseteze încercările la 1
            message_spv.download_from_spv()
            self.assertEqual(message_spv.download_attempts, 1)
            self.assertEqual(message_spv.last_download_date, fields.Date.today())

    def test_multi_company_isolation(self):
        """Testează izolarea datelor între companii și check_company"""
        company_b = self.env["res.company"].create({"name": "Company B"})

        # Mesaj în Compania A (default)
        message_a = self.env["l10n.ro.message.spv"].create(
            {
                "name": "MSG_A",
                "company_id": self.env.company.id,
            }
        )

        # Atașament în Compania B
        attachment_b = self.env["ir.attachment"].create(
            {
                "name": "file_b",
                "company_id": company_b.id,
                "datas": b"dGVzdA==",
            }
        )

        # Încercarea de a lega atașamentul din Compania B la mesajul din Compania A
        # ar trebui să eșueze din cauza check_company=True
        # Folosim contextul de companie A și un utilizator care nu este super-user
        # pentru a forța verificările de companie (deși check_company ar trebui să
        # funcționeze oricum)
        user = self.env["res.users"].create(
            {
                "name": "Test User",
                "login": "test_user_isolation",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("base.group_multi_company").id,
                            self.env.ref("account.group_account_invoice").id,
                        ],
                    )
                ],
                "company_ids": [(6, 0, [self.env.company.id, company_b.id])],
                "company_id": self.env.company.id,
            }
        )
        with self.assertRaises(AccessError):
            message_a.with_user(user).with_context(
                allowed_company_ids=self.env.company.ids
            ).write({"attachment_id": attachment_b.id})

    def test_cron_error_persistence_with_rollback(self):
        """Testează dacă download_attempts este salvat de cron chiar
        și în caz de excepție Python (rollback)"""
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "TEST_ROLLBACK",
                "company_id": self.env.company.id,
                "state": "draft",
                "download_attempts": 0,
            }
        )

        # Forțăm o excepție în timpul download_from_spv pentru a
        # declanșa rollback-ul tranzacției interne
        with self.assertLogs(
            "odoo.addons.l10n_ro_message_spv.models.res_company", level="ERROR"
        ) as cm:
            with patch.object(
                type(self.env["l10n.ro.message.spv"]),
                "download_from_spv",
                side_effect=Exception("Crash!"),
            ):
                # Rulăm cron-ul (metoda din res.company)
                self.env.company.l10n_ro_download_zip_message_spv(limit=1)

            # Verificăm că eroarea a fost logată
            self.assertTrue(
                any("Eroare la descărcarea ZIP" in log for log in cm.output)
            )

        # Verificăm că, în ciuda crash-ului, cron-ul a salvat eroarea
        # și a incrementat încercările
        message_spv.invalidate_recordset()
        self.assertEqual(message_spv.state, "error")
        self.assertEqual(message_spv.download_attempts, 1)
        self.assertIn("Crash!", message_spv.error)

    def test_received_invoice_edi_state_validated(self):
        """The EDI document created for a received bill must be
        invoice_validated, not invoice_sent."""
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
        self.assertFalse(invoice.l10n_ro_edi_document_ids)

        message_spv.get_data_from_invoice()

        self.assertTrue(invoice.l10n_ro_edi_document_ids)
        self.assertEqual(invoice.l10n_ro_edi_document_ids[0].state, "invoice_validated")
        self.assertEqual(invoice.l10n_ro_edi_state, "invoice_validated")

    def test_out_message_edi_state_validated(self):
        """An out message matched by hand (typically a self-billed invoice the
        customer issued in our name) must get an invoice_validated EDI
        document, not invoice_sent.

        With invoice_sent the fetch-status cron queries ANAF using
        l10n_ro_edi_index — empty, because the upload never left this
        instance — fails on every run and re-triggers itself every 2 minutes
        for as long as an invoice_sent invoice exists, so it never stops."""
        refund = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": self.vendor.id,
                "ref": "00027547122026",
            }
        )
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "MSG_OUT_SELF",
                "request_id": "REQ_OUT_SELF",
                "cif": "123",
                "message_type": "out_invoice",
                "partner_id": self.vendor.id,
                "invoice_id": refund.id,
            }
        )
        self.assertFalse(refund.l10n_ro_edi_document_ids)

        message_spv.get_data_from_invoice()

        self.assertEqual(len(refund.l10n_ro_edi_document_ids), 1)
        self.assertEqual(refund.l10n_ro_edi_document_ids[0].state, "invoice_validated")
        self.assertEqual(refund.l10n_ro_edi_state, "invoice_validated")
        # The state is no longer the one the fetch-status cron queries, and
        # re-sending stays blocked: _is_ro_edi_applicable requires an empty
        # l10n_ro_edi_state.
        self.assertNotIn(refund.l10n_ro_edi_state, (False, "invoice_sent"))

    def test_out_message_keeps_existing_edi_document(self):
        """Invoices uploaded by this very instance already have an EDI document
        holding the index: matching must not touch their state, so the normal
        invoice_sent -> invoice_validated flow (and the signature retrieval)
        stays unchanged."""
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.vendor.id,
            }
        )
        existing = self.env["l10n_ro_edi.document"].create(
            {
                "invoice_id": invoice.id,
                "state": "invoice_sent",
                "key_loading": "OWN_UPLOAD",
            }
        )
        message_spv = self.env["l10n.ro.message.spv"].create(
            {
                "name": "MSG_OUT_OWN",
                "request_id": "REQ_OUT_OWN",
                "cif": "123",
                "message_type": "out_invoice",
                "partner_id": self.vendor.id,
                "invoice_id": invoice.id,
            }
        )

        message_spv.get_data_from_invoice()

        self.assertEqual(invoice.l10n_ro_edi_document_ids, existing)
        self.assertEqual(invoice.l10n_ro_edi_state, "invoice_sent")
