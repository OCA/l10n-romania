# -*- coding: utf-8 -*-
import datetime
from openerp import api, fields, models, _


class ResPartner(models.Model):
	_inherit = "res.partner"
	_name = "res.partner"	
	
	tax_scheme_id = fields.Many2one('unece.code.list', string="Tax Scheme", help="Partner's Tax Scheme for E-invoice", domain=[('type', '=', 'tax_scheme')])