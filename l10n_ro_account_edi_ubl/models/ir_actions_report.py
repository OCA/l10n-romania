# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
from xml.sax.saxutils import escape, quoteattr

from lxml import etree

from odoo import api, models
from odoo.tools import cleanup_xml_node


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _postprocess_pdf_report(self, record, buffer):
        """
        EXTENDS account
        Add the pdf report in XML as base64 string.
        """
        result = super()._postprocess_pdf_report(record, buffer)

        if not record.company_id.l10n_ro_edi_cius_embed_pdf:
            return result

        if record._name == "account.move":

            format_codes = ["cius_ro"]
            cius_ro_edi_documents = record.edi_document_ids.filtered(
                lambda d: d.edi_format_id.code in format_codes
            )
            if not cius_ro_edi_documents:
                return result

            invoice_report = self.env.company.l10n_ro_default_cius_pdf_report
            if not invoice_report:
                invoice_report = self.env.ref("account.account_invoices")
            if invoice_report and invoice_report != self:
                return result
            record.attach_ubl_xml_file_button()
            edi_attachments = cius_ro_edi_documents.attachment_id

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
                        record, buffer, tree, anchor_elements, edi_attachment
                    )
        return result

    @api.model
    def l10n_ro_add_pdf_to_xml(
        self, invoice, buffer, tree, anchor_elements, edi_attachment
    ):

        pdf_content_b64 = base64.b64encode(buffer.getvalue()).decode()
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
