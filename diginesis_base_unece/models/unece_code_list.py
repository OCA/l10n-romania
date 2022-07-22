# -*- coding: utf-8 -*-
from openerp import api, fields, models, _


class UneceCodeList(models.Model):
	_name = "unece.code.list"
	_description = "UNECE nomenclatures"
	_order = "type, code"

	code = fields.Char(required=True, copy=False)
	name = fields.Char(required=True, copy=False)
	type = fields.Selection([], required=True)
	description = fields.Text()
	active = fields.Boolean(default=True)

	_sql_constraints = [
		(
			"type_code_uniq",
			"unique(type, code)",
			"An UNECE code of the same type already exists",
		)
	]

	@api.multi
	def name_get(self):
		res = []
		for entry in self:
			res.append((entry.id, "[{}] {}".format(entry.code, entry.name)))
		return res

	@api.model
	def name_search(self, name="", args=None, operator="ilike", limit=80):
		if args is None:
			args = []
		if name and operator == "ilike":
			recs = self.search([("code", "=", name)] + args, limit=limit)
			if recs:
				return recs.name_get()
		return super(UneceCodeList, self).name_search(name=name, args=args, operator=operator, limit=limit)
