# -*- coding: utf-8 -*-
# ©  2015 Forest and Biomass Services Romania
# See README.rst file on addons root folder for license details

from openerp import models, fields, api


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _get_vat_on_payment(self):
        res = super(AccountInvoice, self)._get_vat_on_payment()
        inv_type = self._context.get('type', 'out_invoice')
        if 'out' not in inv_type:
            res = self.partner_id.vat_on_payment
        return res

    fiscal_receipt = fields.Boolean('Is a Fiscal Receipt')

    @api.multi
    def onchange_partner_id(self, type, partner_id, date_invoice=False,
                            payment_term=False, partner_bank_id=False,
                            company_id=False):
        """ Check if invoice is with VAT on Payment.
            Romanian law specify that the VAT on payment is applied only
            for internal invoices (National or not specified fiscal position)
        """
        result = super(AccountInvoice, self).onchange_partner_id(
            type, partner_id, date_invoice, payment_term, partner_bank_id,
            company_id)
        vatp = False
        ctx = dict(self._context)
        if date_invoice:
            ctx.update({'check_date': date_invoice})
        if 'out' in type:
            vatp = self.user_id.company_id.partner_id.with_context(
                ctx)._check_vat_on_payment()
        else:
            partner = self.env['res.partner'].browse(partner_id)
            vatp = partner.with_context(ctx)._check_vat_on_payment()
        result['value']['vat_on_payment'] = vatp
        return result

    @api.onchange("fiscal_receipt", "fiscal_position")
    def onchange_fiscal_receipt(self):
        """ Check for partner vat on payment if the invoice is not
            a fiscal receipt, and the national fiscal position is set."""
        vatp = False
        if not self.fiscal_receipt:
            ctx = dict(self._context)
            if self.date_invoice:
                ctx.update({'check_date': self.date_invoice})
            if (not self.fiscal_position or
                    'National' in self.fiscal_position.name):
                vatp = self.partner_id.with_context(
                    ctx)._check_vat_on_payment()
        self.vat_on_payment = vatp
