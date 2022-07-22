# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT


class SaleOrder(models.Model):
	_name = "sale.order"
	_inherit = "sale.order"

	@api.multi
	def _prepare_invoice(self):
		res = super(SaleOrder, self)._prepare_invoice()
		
		res.update({'is_state_institution': self.partner_invoice_id and self.partner_invoice_id.is_state_institution or False})
		
		return res