# -*- coding: utf-8 -*-
import datetime
from openerp import api, fields, models, _


class ResPartner(models.Model):
	_inherit = "res.partner"
	_name = "res.partner"	
	
	is_state_institution = fields.Boolean("State Institution", default=False)