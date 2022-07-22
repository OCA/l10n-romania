# -*- coding: utf-8 -*-
from openerp import api, fields, models, _


class UneceCodeList(models.Model):
	_inherit = "unece.code.list"

	type = fields.Selection(
		selection_add=[
			("tax_type", "Tax Types (UNCL 5153)"),
			("tax_categ", "Tax Categories (UNCL 5305)"),
			("tax_scheme", "Tax Scheme for Partners"),
		]
	)
