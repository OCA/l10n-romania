# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError,ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

# fields stored in case of some future partner modification, the reports to have the values form invoice time
#    partner_vat = fields.Char(related="partner_id.vat",  store=True) # not working 
    partner_stored_vat = fields.Char('VAT nr',compute='_compute_vat_store',  store=True) 

# exist invoice_partner_display_name(stored char) and  commercial_partner_id (stored res_partner)    

    @api.depends('partner_id') 
    def _compute_vat_store(self):
        for record in self:
            if record.partner_id and record.partner_id.vat:
                record.partner_stored_vat = record.partner_id.vat
            else:
                record.partner_stored_vat  = '' 