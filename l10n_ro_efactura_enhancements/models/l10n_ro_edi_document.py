import base64
import requests
import logging
import json

from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class L10n_ROEdiDocument(models.Model):
    _inherit = "l10n_ro_edi.document"

    xml_attachment = fields.Binary(string="XML Attachment", readonly=True)

    # add PDF in attachment when fetching invoices
    def action_l10n_ro_edi_download_attachment(self):
        # super().action_l10n_ro_edi_download_attachment()
        _logger.info("Fetching sent documents for invoice %s", self.id)
        xml_file = base64.b64decode(self.xml_attachment)
        headers = {"Content-Type": "text/plain"}
        xml = xml_file
        val1 = "FACT1"
        if b"<CreditNote" in xml:
            val1 = "FCN"
        
        url = f"https://webservicesp.anaf.ro/prod/FCTEL/rest/transformare/{val1}"

        res = requests.post(url, data=xml, headers=headers, timeout=25)
        if "The requested URL was rejected" in res.text:
            raise UserError(_("ANAF service unable to generate PDF from this XML."))
        if res.status_code == 200:
            _logger.error(f"PDF CONTENT {res.content}")
            if res.content:
                if b'"stare":"nok"' in res.content:
                    try:
                        response_data = json.loads(res.content.decode('utf-8'))
                        error_message = response_data['Messages']
                        raise UserError(_("ANAF service error: %s") % error_message)
                    except json.JSONDecodeError:
                        raise UserError(_("ANAF service error: %s") % res.content.decode('utf-8'))
                
                pdf = base64.b64encode(res.content)
                file_name = f"{self.invoice_id.l10n_ro_edi_index}.pdf"

                attachment_value = {
                    "name": file_name,
                    "datas": pdf,
                    "res_model": "account.move",
                    "res_id": self.invoice_id.id,
                    "type": "binary",
                    "mimetype": "application/pdf",
                }
                attachment_pdf = self.env["ir.attachment"].sudo().create(attachment_value)
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment_pdf.id}?download=true',
            'target': 'self',
        }

