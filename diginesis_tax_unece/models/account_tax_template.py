# -*- coding: utf-8 -*-
from openerp import api, fields, models, _


class AccountTaxTemplate(models.Model):
	_inherit = "account.tax.template"

	unece_type_id = fields.Many2one(
		"unece.code.list",
		string="UNECE Tax Type",
		domain=[("type", "=", "tax_type")],
		help="Select the Tax Type Code of the official "
		"nomenclature of the United Nations Economic "
		"Commission for Europe (UNECE), DataElement 5153",
	)
	unece_categ_id = fields.Many2one(
		"unece.code.list",
		string="UNECE Tax Category",
		domain=[("type", "=", "tax_categ")],
		help="Select the Tax Category Code of the official "
		"nomenclature of the United Nations Economic "
		"Commission for Europe (UNECE), DataElement 5305",
	)

	def _get_tax_vals(self, company):
		self.ensure_one()
		res = super(AccountTaxTemplate, self)._get_tax_vals(company)
		res["unece_type_id"] = self.unece_type_id.id
		res["unece_categ_id"] = self.unece_categ_id.id
		return res
