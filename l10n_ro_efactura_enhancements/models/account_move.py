import requests
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.addons.l10n_ro_edi.models.utils import _request_ciusro_synchronize_invoices
from odoo.addons.l10n_ro_edi.models.account_move import HOLDING_DAYS

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

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

