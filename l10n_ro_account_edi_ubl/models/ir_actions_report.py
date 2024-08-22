# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from xml.sax.saxutils import escape, quoteattr

from lxml import etree

from odoo import api, models
from odoo.tools import cleanup_xml_node


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        # EXTENDS base
        # Allow other pdf report to be embedded in the xml cius file.
        collected_streams = super()._render_qweb_pdf_prepare_streams(
            report_ref, data, res_ids=res_ids
        )
        pdf_report = self.env.company.l10n_ro_default_cius_pdf_report
        if not pdf_report:
            pdf_report = self.env.ref("account.account_invoices")
        if (
            collected_streams
            and res_ids
            and self._get_report(report_ref).report_name == pdf_report.report_name
        ):
            for res_id, stream_data in collected_streams.items():
                invoice = self.env["account.move"].browse(res_id)
                self._add_pdf_into_invoice_xml(invoice, stream_data)
        return collected_streams

    def _add_pdf_into_invoice_xml(self, invoice, stream_data):
        """
        EXTENDS account
        Add the pdf report in XML as base64 string.
        """
        result = super()._add_pdf_into_invoice_xml(invoice, stream_data)
        if invoice.company_id.l10n_ro_edi_cius_embed_pdf:
            cius_ro = self.env.ref("l10n_ro_account_edi_ubl.edi_ubl_cius_ro")
            edi_attachments = invoice._get_edi_attachment(cius_ro)
            for edi_attachment in edi_attachments:
                old_xml = base64.b64decode(
                    edi_attachment.with_context(bin_size=False).datas, validate=True
                )
                tree = etree.fromstring(old_xml)
                anchor_elements = tree.xpath(
                    "//*[local-name()='AccountingSupplierParty']"
                )
                additional_document_elements = tree.xpath(
                    "//*[local-name()='AdditionalDocumentReference']"
                )
                # with this clause, we ensure the xml are only postprocessed once
                # (even when the invoice is reset to draft then validated again)
                if anchor_elements and not additional_document_elements:
                    self.l10n_ro_add_pdf_to_xml(
                        invoice, stream_data, tree, anchor_elements, edi_attachment
                    )
        return result

    @api.model
    def l10n_ro_add_pdf_to_xml(
        self, invoice, stream_data, tree, anchor_elements, edi_attachment
    ):
        pdf_stream = stream_data["stream"]
        pdf_content_b64 = base64.b64encode(pdf_stream.getvalue()).decode()
        pdf_name = "%s.pdf" % invoice.name.replace("/", "_")
        to_inject = """
<cac:AdditionalDocumentReference
    xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
    <cbc:ID>%s</cbc:ID>
    <cac:Attachment>
        <cbc:EmbeddedDocumentBinaryObject mimeCode="application/pdf" filename=%s>
            %s
        </cbc:EmbeddedDocumentBinaryObject>
    </cac:Attachment>
</cac:AdditionalDocumentReference>
        """ % (
            escape(pdf_name),
            quoteattr(pdf_name),
            pdf_content_b64,
        )

        anchor_index = tree.index(anchor_elements[0])
        tree.insert(anchor_index, etree.fromstring(to_inject))
        new_xml = etree.tostring(
            cleanup_xml_node(tree), xml_declaration=True, encoding="UTF-8"
        )
        edi_attachment.sudo().write(
            {
                "res_model": "account.move",
                "res_id": invoice.id,
                "datas": base64.b64encode(new_xml),
                "mimetype": "application/xml",
            }
        )
