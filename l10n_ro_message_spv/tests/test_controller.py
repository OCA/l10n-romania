# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import io
import zipfile
from unittest.mock import patch

from odoo.tests import HttpCase, tagged
from odoo.tools.misc import file_path

from .common import TestMessageSPV as TestMessageSPVCommon
from .test_message_spv import EMBEDDED_PDF_XML


@tagged("post_install", "-at_install")
class TestMessageSPVController(TestMessageSPVCommon, HttpCase):
    """The XML and the PDFs are streamed on the fly from the stored ZIP."""

    def setUp(self):
        super().setUp()
        # the company record rule allows only the session's companies: put
        # the admin HTTP session in the test company
        admin = self.env.ref("base.user_admin")
        admin.write(
            {
                "company_ids": [(4, self.env.company.id)],
                "company_id": self.env.company.id,
            }
        )

    def _create_message_with_zip(self, name, request_id, zip_content):
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
                "raw": zip_content,
                "mimetype": "application/zip",
            }
        )
        message.write({"attachment_id": attachment.id, "state": "downloaded"})
        return message

    def _make_zip(self, request_id, xml_bytes):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zip_file:
            zip_file.writestr(f"{request_id}.xml", xml_bytes)
            zip_file.writestr(f"semnatura_{request_id}.xml", b"<signature/>")
        return buf.getvalue()

    def test_download_xml_route(self):
        zip_content = open(
            file_path("l10n_ro_message_spv/tests/invoice.zip"), "rb"
        ).read()
        message = self._create_message_with_zip("CTRL1", "5004111924", zip_content)
        self.env.cr.flush()
        self.authenticate("admin", "admin")

        response = self.url_open(f"/l10n_ro/message_spv/{message.id}/xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invoice", response.content)
        self.assertIn("5004111924.xml", response.headers.get("Content-Disposition"))

    def test_download_xml_route_without_zip(self):
        message = self.env["l10n.ro.message.spv"].create(
            {
                "name": "CTRL2",
                "request_id": "NOZIP",
                "company_id": self.env.company.id,
                "message_type": "in_invoice",
            }
        )
        self.authenticate("admin", "admin")
        response = self.url_open(f"/l10n_ro/message_spv/{message.id}/xml")
        self.assertEqual(response.status_code, 404)

    def test_download_embedded_pdf_route(self):
        message = self._create_message_with_zip(
            "CTRL3", "TESTEMB", self._make_zip("TESTEMB", EMBEDDED_PDF_XML)
        )
        self.authenticate("admin", "admin")
        response = self.url_open(f"/l10n_ro/message_spv/{message.id}/embedded_pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"%PDF-test")
        self.assertIn("embedded.pdf", response.headers.get("Content-Disposition"))

    def test_download_embedded_pdf_route_absent(self):
        message = self._create_message_with_zip(
            "CTRL4", "TESTNOPDF", self._make_zip("TESTNOPDF", b"<Invoice/>")
        )
        self.authenticate("admin", "admin")
        response = self.url_open(f"/l10n_ro/message_spv/{message.id}/embedded_pdf")
        self.assertEqual(response.status_code, 404)

    def test_download_anaf_pdf_route(self):
        message = self._create_message_with_zip(
            "CTRL5", "TESTANAF", self._make_zip("TESTANAF", b"<Invoice/>")
        )
        self.authenticate("admin", "admin")
        with patch.object(
            type(self.env["l10n.ro.message.spv"]),
            "_render_anaf_pdf_bytes",
            return_value=b"%PDF-anaf",
        ):
            response = self.url_open(f"/l10n_ro/message_spv/{message.id}/anaf_pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"%PDF-anaf")
        self.assertIn("TESTANAF.pdf", response.headers.get("Content-Disposition"))
