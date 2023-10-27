# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountEdiDocument(models.Model):
    _name = 'account.edi.document'
    _inherit = ['account.edi.document', 'mail.thread']

    step = fields.Integer(default=0, help="Current step in the flow", copy=False)
    l10n_ro_edi_transaction = fields.Char(related="move_id.l10n_ro_edi_transaction")
    l10n_ro_edi_download = fields.Char(related="move_id.l10n_ro_edi_download")
    response_state = fields.Selection([('success', 'Success'), ('error', 'Error')], copy=False, tracking=True)
    message_state = fields.Selection([('found_ok', 'Found - Ok'), ('missing', 'Missing'), ('found_notok', 'Found - Not Ok'), ('found_processing', 'Found - Pending')], copy=False)
    response_attachment_id = fields.Many2one('ir.attachment', "Response ZIP", copy=False, help="The file received. Contains either the original invoice or a list of error found for the invoice during processing.")
    edi_format_code = fields.Char('Format Code', related='edi_format_id.code', store=True, copy=False)

    def _cron_get_response_web_service(self):
        """ Get all documents with l10n_ro_edi_transaction and without response_attachment_id """

        documents = self.search([('l10n_ro_edi_transaction', '!=', False), ('response_attachment_id', '=', False), ('move_id', '!=', False), ('edi_format_id', '!=', False)])
        for doc in documents.filtered(lambda x: x.move_id.state == 'posted' and x.edi_format_id.code == "cius_ro"):
            doc._process_step_1_response(doc.edi_format_id._l10n_ro_get_message_state_web_service(doc.move_id))
            if doc.message_state in ['found_ok', 'found_notok']:
                doc._process_step_2_response(doc.edi_format_id._l10n_ro_get_message_response_web_service(doc.move_id))

        return True

    def _process_step_1_response(self, response):
        self.ensure_one()
        response_to_state_map = {"ok": "found_ok", "pending": "found_processing", "missing": "missing", "nok": "found_notok"}

        state = response.get('response')
        vals = {'message_state': response_to_state_map.get(state) or "missing" }
        if response.get('error'):
            vals.update({'error': "{0}<br/>{1}".format(self.error or '', response['error'])})

        self.write(vals)

        download_id = response.get('download_id')
        if self.move_id:
            self.move_id.write({'l10n_ro_edi_download': download_id})

        if download_id:
            self.message_post(body=_('Message state successful. Download {0}.').format(download_id))
        else:
            self.message_post(body=_('Message state failed.'))

        return True

    def _process_step_2_response(self, response):
        self.ensure_one()

        vals = {'response_state': 'success'}
        if response.get('error'):
            vals.update({'response_state': 'error', 'error': "{0}<br/>{1}".format(self.error or '', response['error'])})
        elif response.get('response'):
            attachment = self.env["ir.attachment"].create({
                "name": _("ANAF Response.zip"),
                "raw": response.get('response'),
                "mimetype": "application/x-zip",
                "res_model": self._name,
                "res_id": self.id,
            })
            vals.update({'response_attachment_id': attachment.id})

        self.write(vals)
        if vals.get('response_attachment_id'):
            self.message_post(body=_('Response state successful.'))
        else:
            self.message_post(body=_('Response state failed.'))

        return True
