# -*- coding: utf-8 -*-
from openerp import api, fields, models, _


class AccountTax(models.Model):
	_inherit = "account.tax"

	unece_type_id = fields.Many2one(
		"unece.code.list",
		string="UNECE Tax Type",
		domain=[("type", "=", "tax_type")],
		ondelete="restrict",
		help="Select the Tax Type Code of the official "
		"nomenclature of the United Nations Economic "
		"Commission for Europe (UNECE), DataElement 5153",
	)
	unece_type_code = fields.Char(
		related="unece_type_id.code",
		store=True,
		readonly=True,
		string="UNECE Type Code",
	)
	unece_categ_id = fields.Many2one(
		"unece.code.list",
		string="UNECE Tax Category",
		domain=[("type", "=", "tax_categ")],
		ondelete="restrict",
		help="Select the Tax Category Code of the official "
		"nomenclature of the United Nations Economic "
		"Commission for Europe (UNECE), DataElement 5305",
	)
	unece_categ_code = fields.Char(
		related="unece_categ_id.code",
		store=True,
		readonly=True,
		string="UNECE Category Code",
	)

	@api.model
	def _get_tax_exigibility_from_unece_code(self, unece_code):
		if isinstance(unece_code, int):
			unece_code = str(unece_code)
		mapping = {
			"5": "on_invoice",
			"29": "on_invoice",
			"72": "on_payment",
		}
		if unece_code in mapping:
			return mapping[unece_code]
		else:
			return None

	def _get_unece_due_date_type_code(self, tax_exigibility):
		self.ensure_one()
		mapping = {
			"on_invoice": "5",
			"on_payment": "72",
		}
		return mapping.get(tax_exigibility)	   
