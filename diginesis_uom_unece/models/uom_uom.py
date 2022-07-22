# -*- coding: utf-8 -*-
from odoo import api, fields, tools, models, _
from odoo.exceptions import UserError, ValidationError


class UoM(models.Model):
	_name = 'uom.uom'
	_inherit = 'uom.uom'
	
	unece_code = fields.Char(string="UNECE Code", help="Standard nomenclature of the United Nations Economic Commission for Europe (UNECE).",)
	