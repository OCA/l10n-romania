import base64
import requests
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.addons.l10n_ro_edi.models.utils import _request_ciusro_synchronize_invoices, _request_ciusro_fetch_status, _request_ciusro_download_answer
from odoo.addons.l10n_ro_edi.models.account_move import HOLDING_DAYS

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _l10n_ro_edi_process_bill_messages(self, received_bills_messages):
        super()._l10n_ro_edi_process_bill_messages(received_bills_messages)
        for message in received_bills_messages:
            if 'error' in message['answer']:
                continue
                
            bill = self.env['account.move'].search([
                ('l10n_ro_edi_index', '=', message['id_solicitare']),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            
            if bill:
                edi_docs = bill.l10n_ro_edi_document_ids
                for doc in edi_docs:
                    doc.xml_attachment = base64.b64encode(message['answer']['invoice']['attachment_raw'] or b'')


    def _l10n_ro_edi_fetch_invoice_sent_documents(self):
        """
        This method loops over all invoice with sending document in `self`. For each of them,
        it pre-checks errors and make a fetch request for the invoice. Then:

         - if no answer is received, it will do nothing on the current invoice
         - if there is an error during the communication with the server -> log it in the chatter
         - else (receives `key_download`) -> immediately make a download request and process it:
            - if there is an error during the communication with the server -> log it in the chatter
            - if 'nok', then the invoice has been refused by ANAF -> create a refused document
            - if 'ok', then the invoice has been accepted by ANAF -> create a success document
        """
        session = requests.Session()
        invoices_to_fetch = self.filtered(lambda inv: inv.l10n_ro_edi_state == 'invoice_sent')
        documents_to_create = []
        document_ids_to_delete = []

        for invoice in invoices_to_fetch:
            self.env['res.company']._with_locked_records(invoice)
            result = _request_ciusro_fetch_status(
                company=invoice.company_id,
                key_loading=invoice.l10n_ro_edi_index,
                session=session,
            )
            if not result:  # SPV is still processing the XML (no answer yet); do nothing
                invoice.message_post(body=_("SPV has not finished processing the invoice, try again later."))
                continue

            if 'error' in result:  # Fetch error
                invoice.message_post(body=_(
                    "Error when trying to fetch the E-Factura status from the SPV: %s",
                    result['error']
                ))
                continue

            # SPV finished the validation process and sent us an answer containing: `key_download`` a key
            # to obtain the signature and, if the invoice is refused, the reason why.
            download_data = _request_ciusro_download_answer(
                company=invoice.company_id,
                key_download=result['key_download'],
                session=session,
            )
            if 'error' in download_data:  # Fetch error
                invoice.message_post(body=_(
                    "Error when trying to download the E-Factura data from the SPV: %s",
                    result['error']
                ))
                continue

            document_ids_to_delete += invoice.l10n_ro_edi_document_ids.ids
            #added xml_attachment field with the xml of the invoice
            document_data = {
                'invoice_id': invoice.id,
                'key_download': result['key_download'],
                'key_signature': download_data['signature']['key_signature'],
                'key_certificate': download_data['signature']['key_certificate'],
                'attachment': base64.b64encode(download_data['signature']['attachment_raw']),
                'xml_attachment': base64.b64encode(download_data['invoice']['attachment_raw']),
            }
            if result['state_status'] == 'nok':  # Invoice refused
                error_message = download_data['invoice']['error'].replace('\t', '')
                invoice.message_post(body=_(
                    "This invoice was refused by the SPV for the following reason: %s",
                    error_message
                ))
                document_data.update({
                    'state': 'invoice_refused',
                    'message': error_message,
                })
            else:  # Invoice accepted
                invoice.message_post(body=_("This invoice has been accepted by the SPV."))
                document_data['state'] = 'invoice_validated'

            documents_to_create.append(document_data)

        self.env['l10n_ro_edi.document'].sudo().browse(document_ids_to_delete).unlink()
        self.env['l10n_ro_edi.document'].sudo().create(documents_to_create)
        if self._can_commit():
            self.env.cr.commit()

    def _l10n_ro_edi_send_invoice(self, xml_data):
        super()._l10n_ro_edi_send_invoice(xml_data)
        for doc in self.l10n_ro_edi_document_ids:
            doc.xml_attachment = base64.b64encode(xml_data)

    # Function from odoo l10n_ro_edi module with days sent as parameter
    @api.model
    def _l10n_ro_edi_fetch_invoices(self):
        """ Synchronize bills/invoices from SPV """
        days = self.env.company.l10n_ro_download_einvoices_days if self.env.company.l10n_ro_download_einvoices_days else 1

        result = _request_ciusro_synchronize_invoices(
            company=self.env.company,
            session=requests.Session(),
            nb_days=days
        )
        if 'error' in result:
            raise UserError(result['error'])

        if result['sent_invoices_accepted_messages']:
            self._l10n_ro_edi_process_invoice_accepted_messages(result['sent_invoices_accepted_messages'])

        if result['sent_invoices_refused_messages']:
            self._l10n_ro_edi_process_invoice_refused_messages(result['sent_invoices_refused_messages'])

        if result['received_bills_messages']:
            self._l10n_ro_edi_process_bill_messages(result['received_bills_messages'])

        # Non-indexed moves that were not processed after some time have probably been refused by the SPV. Since
        # there is no way to recover the index for refused invoices, we simply refuse them manually without proper reason.
        domain = (
            Domain('company_id', '=', self.env.company.id)
            & Domain('l10n_ro_edi_index', '=', False)
            & Domain('l10n_ro_edi_state', '=', 'invoice_not_indexed')
        )
        non_indexed_invoices = self.env['account.move'].search(domain)

        document_ids_to_delete = []
        for invoice in non_indexed_invoices:
            # At that point, only one sent document should exists on an invoice
            sent_document = invoice.l10n_ro_edi_document_ids

            if (fields.Datetime.today() - sent_document.create_date).days > HOLDING_DAYS:
                document_ids_to_delete += invoice.l10n_ro_edi_document_ids.ids

                error_message = _(
                    "The invoice has probably been refused by the SPV. We were unable to recover the reason of the refusal because "
                    "the invoice had not received its index. Duplicate the invoice and attempt to send it again."
                )
                invoice.message_post(body=error_message)
                self.env['l10n_ro_edi.document'].sudo().create({
                    'invoice_id': invoice.id,
                    'state': 'invoice_refused',
                    'message': error_message,
                })

        self.env['l10n_ro_edi.document'].sudo().browse(document_ids_to_delete).unlink()

        if self._can_commit():
            self.env.cr.commit()

    #reset to draft invoices from spv
    @api.depends('l10n_ro_edi_state')
    def _compute_show_reset_to_draft_button(self):
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.move_type == 'in_invoice' and move.state != 'draft':
                move.show_reset_to_draft_button = True

