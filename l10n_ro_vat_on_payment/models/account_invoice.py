# Copyright  2015 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        """ Check if invoice is with VAT on Payment.
            Romanian law specify that the VAT on payment is applied only
            for internal invoices (National or not specified fiscal position)
        """
        result = super(AccountInvoice, self)._onchange_partner_id()
        fp_model = self.env['account.fiscal.position']
        vatp = False
        ctx = dict(self._context)
        company_id = self.company_id.id
        partner = self.partner_id if not company_id else \
            self.partner_id.with_context(force_company=company_id)
        if self.date_invoice:
            ctx.update({'check_date': self.date_invoice})
        if 'out' in self.type:
            vatp = company_id.partner_id.with_context(
                ctx)._check_vat_on_payment()
        else:
            vatp = partner.with_context(ctx)._check_vat_on_payment()
        if vatp:
            fptvainc = fp_model.search(
                [('name', 'ilike', 'Regim TVA la Incasare')])
            if fptvainc:
                self.fiscal_position_id = fptvainc
        return result
