# Copyright (C) 2026 Dorin Hongu <dhongu(@)gmail(.)com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import http
from odoo.http import content_disposition, request


class MessageSPVController(http.Controller):
    """Serve files derived on the fly from the stored ANAF ZIP.

    Only the signed ZIP is persisted on the SPV message; the XML and the
    PDFs are extracted/rendered on demand so they never take up filestore
    space."""

    def _get_message(self, message_id):
        message = request.env["l10n.ro.message.spv"].browse(message_id)
        message.check_access("read")
        return message

    def _make_download(self, content, file_name, mimetype):
        return request.make_response(
            content,
            headers=[
                ("Content-Type", mimetype),
                ("Content-Length", len(content)),
                ("Content-Disposition", content_disposition(file_name)),
            ],
        )

    @http.route(
        "/l10n_ro/message_spv/<int:message_id>/xml",
        type="http",
        auth="user",
        readonly=True,
    )
    def download_xml(self, message_id, **kwargs):
        message = self._get_message(message_id)
        file_name, xml_bytes = message._get_xml_bytes()
        if not xml_bytes:
            raise request.not_found()
        return self._make_download(xml_bytes, file_name, "application/xml")

    @http.route(
        "/l10n_ro/message_spv/<int:message_id>/anaf_pdf",
        type="http",
        auth="user",
        readonly=True,
    )
    def download_anaf_pdf(self, message_id, **kwargs):
        message = self._get_message(message_id)
        pdf_bytes = message._render_anaf_pdf_bytes()
        file_name = f"{message.request_id}.pdf"
        return self._make_download(pdf_bytes, file_name, "application/pdf")

    @http.route(
        "/l10n_ro/message_spv/<int:message_id>/embedded_pdf",
        type="http",
        auth="user",
        readonly=True,
    )
    def download_embedded_pdf(self, message_id, **kwargs):
        message = self._get_message(message_id)
        file_name, pdf_bytes = message._get_embedded_pdf_bytes()
        if not pdf_bytes:
            raise request.not_found()
        return self._make_download(pdf_bytes, file_name, "application/pdf")
