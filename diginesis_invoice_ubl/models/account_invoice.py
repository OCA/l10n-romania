# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import UserError
import base64
from lxml import etree
from openerp.tools import float_compare, float_round,float_is_zero

import logging
logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
	_name = "account.invoice"
	_inherit = ["account.invoice", "base.ubl"]
	
	is_state_institution = fields.Boolean("Institution of State", related="partner_id.is_state_institution", store=True, default=False)
	ubl_number = fields.Char("UBL Number")
	
	@api.multi
	def attach_ubl_xml_file_button(self):
		self.ensure_one()
		
		assert self.type in ("out_invoice", "out_refund")
		assert self.state in ['open', 'paid']
		
		version = self.get_ubl_version()
		xml_string = self.generate_ubl_xml_string(version=version)
		filename = self.get_ubl_filename(version=version)
		
		attach = self.env["ir.attachment"].create({"res_model": self._name, 
														"res_id": self.id, 
														"name": filename, 
														"datas": base64.encodestring(xml_string), 
														"datas_fname" : filename,
														'type': 'binary'})
		
		self.message_post(body=_('UBL XML generated.'))
		return True
	
	
	@api.multi
	def action_cancel(self):
		if self.filtered(lambda x: x.type in ['out_invoice', 'out_refund'] and x.ubl_number):
			raise UserError(_('You cannot cancel invoices with assigned UBL Number.'))		
		return super(AccountInvoice, self).action_cancel()
	
	@api.model
	def get_ubl_filename(self, version="2.1"):
		return "UBL-Invoice-%s.xml" % version

	@api.model
	def get_ubl_version(self):
		return self.env.context.get("ubl_version") or "2.1"
	
	@api.multi
	def get_ubl_lang(self):
		self.ensure_one()
		return self.partner_id.lang or "en_US"
	
	@api.multi
	def _ubl_add_header(self, parent_node, ns, version="2.1"):
		"""Invoice number: max 30 chars """
		self.ensure_one()
		ubl_version = etree.SubElement(parent_node, ns["cbc"] + "CustomizationID")
		ubl_version.text = "urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.0"
		doc_id = etree.SubElement(parent_node, ns["cbc"] + "ID")
		doc_id.text = self._prepare_invoice_number(self.number)
		issue_date = etree.SubElement(parent_node, ns["cbc"] + "IssueDate")
		issue_date.text = self.date_invoice and fields.Date.to_string(self.date_invoice) or ''
		if self.date_due:
			due_date = etree.SubElement(parent_node, ns["cbc"] + "DueDate")
			due_date.text = fields.Date.to_string(self.date_due)
		type_code = etree.SubElement(parent_node, ns["cbc"] + "InvoiceTypeCode")
		type_code.text = self._ubl_get_invoice_type_code()
		#Comment invoice note - not sure if valid
		#if self.comment:
		#	note = etree.SubElement(parent_node, ns["cbc"] + "Note")
		#	note.text = self.comment		
		doc_currency = etree.SubElement(parent_node, ns["cbc"] + "DocumentCurrencyCode")
		doc_currency.text = self.currency_id.name
				

	@api.multi
	def _ubl_get_invoice_type_code(self):
		if self.type == "out_invoice":
			return "380"
		elif self.type == "out_refund":
			return "381"

	@api.multi
	def _ubl_get_order_reference(self):
		"""This method is designed to be inherited"""
		return self.origin

	@api.multi
	def _ubl_add_order_reference(self, parent_node, ns, version="2.1"):
		self.ensure_one()
		sale_order_ref = self._ubl_get_order_reference()
		if sale_order_ref:
			order_ref = etree.SubElement(parent_node, ns["cac"] + "OrderReference")
			order_ref_id = etree.SubElement(order_ref, ns["cbc"] + "ID")
			order_ref_id.text = sale_order_ref

	@api.multi
	def _ubl_get_contract_document_reference_dict(self):
		"""Result: dict with key = Doc Type Code, value = ID"""
		self.ensure_one()
		return {}

	@api.multi
	def _ubl_add_contract_document_reference(self, parent_node, ns, version="2.1"):
		self.ensure_one()
		cdr_dict = self._ubl_get_contract_document_reference_dict()
		for doc_type_code, doc_id in cdr_dict.items():
			cdr = etree.SubElement(parent_node, ns["cac"] + "ContractDocumentReference")
			cdr_id = etree.SubElement(cdr, ns["cbc"] + "ID")
			cdr_id.text = doc_id
			cdr_type_code = etree.SubElement(cdr, ns["cbc"] + "DocumentTypeCode")
			cdr_type_code.text = doc_type_code

	@api.multi
	def _ubl_add_legal_monetary_total(self, parent_node, ns, version="2.1"):
		self.ensure_one()
		monetary_total = etree.SubElement(parent_node, ns["cac"] + "LegalMonetaryTotal")
		cur_name = self.currency_id.name
		prec = self.currency_id.decimal_places
		line_total = etree.SubElement(
			monetary_total, ns["cbc"] + "LineExtensionAmount", currencyID=cur_name
		)
		line_total.text = "%0.*f" % (prec, self.amount_untaxed)
		tax_excl_total = etree.SubElement(
			monetary_total, ns["cbc"] + "TaxExclusiveAmount", currencyID=cur_name
		)
		tax_excl_total.text = "%0.*f" % (prec, self.amount_untaxed)
		tax_incl_total = etree.SubElement(
			monetary_total, ns["cbc"] + "TaxInclusiveAmount", currencyID=cur_name
		)
		tax_incl_total.text = "%0.*f" % (prec, self.amount_total)
		#Remove prepaid amount not sure if ANAF will validate
		#prepaid_amount = etree.SubElement(
		#	monetary_total, ns["cbc"] + "PrepaidAmount", currencyID=cur_name
		#)
		#prepaid_value = self.amount_total - self.residual
		#prepaid_amount.text = "%0.*f" % (prec, prepaid_value)
		payable_amount = etree.SubElement(
			monetary_total, ns["cbc"] + "PayableAmount", currencyID=cur_name
		)
		payable_amount.text = "%0.*f" % (prec, self.residual)

	@api.multi
	def _ubl_add_invoice_line(self, parent_node, iline, line_number, ns, version="2.1"):
		self.ensure_one()
		cur_name = self.currency_id.name
		line_root = etree.SubElement(parent_node, ns["cac"] + "InvoiceLine")
		dpo = self.env["decimal.precision"]
		qty_precision = dpo.precision_get("Product Unit of Measure")
		price_precision = dpo.precision_get("Product Price")
		account_precision = self.currency_id.decimal_places
		line_id = etree.SubElement(line_root, ns["cbc"] + "ID")
		line_id.text = str(line_number)
		uom_unece_code = False
		# product_uom_id is not a required field on account.move.line
		if iline.uom_id.unece_code:
			uom_unece_code = iline.uom_id.unece_code
			quantity = etree.SubElement(
				line_root, ns["cbc"] + "InvoicedQuantity", unitCode=uom_unece_code
			)
		else:
			quantity = etree.SubElement(line_root, ns["cbc"] + "InvoicedQuantity")
		qty = iline.quantity
		quantity.text = "%0.*f" % (qty_precision, qty)
		line_amount = etree.SubElement(
			line_root, ns["cbc"] + "LineExtensionAmount", currencyID=cur_name
		)
		line_amount.text = "%0.*f" % (account_precision, iline.price_subtotal)
		self._ubl_add_invoice_line_tax_total(iline, line_root, ns, version=version)
		self._ubl_add_item(
			iline.name, iline.product_id, line_root, ns, type_="sale", version=version
		)
		price_node = etree.SubElement(line_root, ns["cac"] + "Price")
		price_amount = etree.SubElement(
			price_node, ns["cbc"] + "PriceAmount", currencyID=cur_name
		)
		price_unit = 0.0
		# Use price_subtotal/qty to compute price_unit to be sure
		# to get a *tax_excluded* price unit
		if not float_is_zero(qty, precision_digits=qty_precision):
			price_unit = float_round(
				iline.price_subtotal / float(qty), precision_digits=price_precision
			)
		price_amount.text = "%0.*f" % (price_precision, price_unit)
		#Removed for ANAF - not sure if this will validate
		#if uom_unece_code:
		#	base_qty = etree.SubElement(
		#		price_node, ns["cbc"] + "BaseQuantity", unitCode=uom_unece_code
		#	)
		#else:
		#	base_qty = etree.SubElement(price_node, ns["cbc"] + "BaseQuantity")
		#base_qty.text = "%0.*f" % (qty_precision, qty)

	@api.multi
	def _ubl_add_invoice_line_tax_total(self, iline, parent_node, ns, version="2.1"):
		return
		self.ensure_one()
		cur_name = self.currency_id.name
		prec = self.currency_id.decimal_places
		tax_total_node = etree.SubElement(parent_node, ns["cac"] + "TaxTotal")
		price = iline.price_unit * (1 - (iline.discount or 0.0) / 100.0)
		res_taxes = iline.invoice_line_tax_ids.compute_all(
			price,
			quantity=iline.quantity,
			product=iline.product_id,
			partner=self.partner_id,
		)
		tax_total = float_round(
			res_taxes["total_included"] - res_taxes["total_excluded"],
			precision_digits=prec,
		)
		tax_amount_node = etree.SubElement(
			tax_total_node, ns["cbc"] + "TaxAmount", currencyID=cur_name
		)
		tax_amount_node.text = "%0.*f" % (prec, tax_total)
		if not float_is_zero(tax_total, precision_digits=prec):
			for res_tax in res_taxes["taxes"]:
				tax = self.env["account.tax"].browse(res_tax["id"])
				# we don't have the base amount in res_tax :-(
				self._ubl_add_tax_subtotal(
					False,
					res_tax["amount"],
					tax,
					cur_name,
					tax_total_node,
					ns,
					version=version,
				)

	@api.multi
	def _ubl_add_tax_total(self, xml_root, ns, version="2.1"):
		self.ensure_one()
		cur_name = self.currency_id.name
		tax_total_node = etree.SubElement(xml_root, ns["cac"] + "TaxTotal")
		tax_amount_node = etree.SubElement(
			tax_total_node, ns["cbc"] + "TaxAmount", currencyID=cur_name
		)
		prec = self.currency_id.decimal_places
		tax_amount_node.text = "%0.*f" % (prec, self.amount_tax)
		if not float_is_zero(self.amount_tax, precision_digits=prec):
			res = {}
			for line in self.tax_line_ids:
				key = line.tax_id
				res.setdefault(key,	{"base": 0.0, "amount": 0.0, "tax": False})
				
				res[key]["amount"] += line.amount
				res[key]["base"] += line.base
				res[key]["tax"] = line.tax_id
					
			res = sorted(res.items(), key=lambda l: l[0].sequence)
			for _group, amounts in res:
				self._ubl_add_tax_subtotal(
					amounts["base"],
					amounts["amount"],
					amounts["tax"],
					cur_name,
					tax_total_node,
					ns,
					version=version,
				)
				
	@api.model
	def _ubl_get_tax_scheme_dict_from_partner(self, commercial_partner):
		res = super(AccountInvoice, self)._ubl_get_tax_scheme_dict_from_partner(commercial_partner)
		new_id=False
		if commercial_partner and commercial_partner.tax_scheme_id and commercial_partner.tax_scheme_id.code:
			if commercial_partner.tax_scheme_id.code == 'VAT':
				new_id=commercial_partner.tax_scheme_id.code
		res.update({"id": new_id})
			
		return res
	
	@api.multi
	def generate_invoice_ubl_xml_etree(self, version="2.1"):
		self.ensure_one()
		nsmap, ns = self._ubl_get_nsmap_namespace("Invoice-2", version=version)
		xml_root = etree.Element("Invoice", nsmap=nsmap)
		self._ubl_add_header(xml_root, ns, version=version)
		#Comment order referenece - not sure if valid
		#self._ubl_add_order_reference(xml_root, ns, version=version)
		self._ubl_add_contract_document_reference(xml_root, ns, version=version)
		
		self._ubl_add_supplier_party(
			False,
			self.company_id,
			"AccountingSupplierParty",
			xml_root,
			ns,
			version=version,
		)
		self._ubl_add_customer_party(
			self.partner_id,
			False,
			"AccountingCustomerParty",
			xml_root,
			ns,
			version=version,
		)
		# the field 'partner_shipping_id' is defined in the 'sale' module
		# Modified to 'address_delivery_id' this is in diginesis_account
		if hasattr(self, "address_delivery_id") and self.address_delivery_id:
			self._ubl_add_delivery(self.address_delivery_id, xml_root, ns)
		# Put paymentmeans block even when invoice is paid ?
		payment_identifier = self.get_payment_identifier()
		payment_mode = self.payment_mode if hasattr(self, "payment_mode") else None
		self._ubl_add_payment_means(
			self.partner_bank_id,
			payment_mode,
			self.date_due,
			xml_root,
			ns,
			payment_identifier=payment_identifier,
			version=version,
		)
		#Removed for ANAF - not sure if this will be validated
		#if self.payment_term_id:
		#	self._ubl_add_payment_terms(
		#		self.payment_term_id, xml_root, ns, version=version
		#	)
		self._ubl_add_tax_total(xml_root, ns, version=version)
		self._ubl_add_legal_monetary_total(xml_root, ns, version=version)

		line_number = 0
		for iline in self.invoice_line_ids:
			line_number += 1
			self._ubl_add_invoice_line(
				xml_root, iline, line_number, ns, version=version
			)
		return xml_root
	
	@api.multi
	def generate_ubl_xml_string(self, version="2.1"):
		self.ensure_one()
		
		assert self.state in ['open', 'paid']
		assert self.type in ("out_invoice", "out_refund")
		
		logger.debug("Starting to generate UBL XML Invoice file")
		lang = self.get_ubl_lang()
		# The aim of injecting lang in context
		# is to have the content of the XML in the partner's lang
		# but the problem is that the error messages will also be in
		# that lang. But the error messages should almost never
		# happen except the first days of use, so it's probably
		# not worth the additional code to handle the 2 langs
		
		self._ubl_validate()
		
		xml_root = self.with_context(lang=lang).generate_invoice_ubl_xml_etree(
			version=version
		)
		xml_string = etree.tostring(
			xml_root, pretty_print=True, encoding="UTF-8", standalone="yes", xml_declaration=True
		)
		#TODO:self._ubl_check_xml_schema(xml_string, "Invoice", version=version)
		logger.debug(
			"Invoice UBL XML file generated for account invoice ID %d " "(state %s)",
			self.id,
			self.state,
		)
		#logger.debug(xml_string.decode("utf-8"))
		return xml_string
	
	@api.multi
	def get_payment_identifier(self):
		self.ensure_one()
		
		return None
	
	@api.model
	def _prepare_invoice_number(self, number):
		return (number or '')[:30]
	
	@api.multi
	def _ubl_validate(self):
		self.ensure_one()
		
		errors = []
				
		errors += self._ubl_validate_invoice(self)
		errors += self._ubl_validate_partner(self.company_id.partner_id)
		errors += self._ubl_validate_partner(self.partner_id)
		
		if errors:
			raise UserError("\n".join(errors))
		
		return True
	
	@api.model
	def _ubl_validate_invoice(self, invoice):
		err = []
		if not self.number:
			err.append(_('Invoice number is required'))
		
		if not self.date_invoice:
			err.append(_('Invoice date is required'))
		
		if hasattr(self, "payment_mode"):	
			if not self.payment_mode:
				err.append(_('Invoice payment mode is required'))
			
		return err
	
	@api.model
	def _ubl_validate_partner(self, partner):
		err = []
		
		if not partner.name:
			err.append(_('Invalid name for partner #{0}').format(partner.id))
		
		if not partner.street:
			err.append(_('Invalid address for partner {0}').format(partner.name or ''))
		
		if not partner.city:
			err.append(_('Invalid city for partner {0}').format(partner.name or ''))
		
		if not partner.country_id:
			err.append(_('Invalid country for partner {0}').format(partner.name or ''))
			
		if not partner.tax_scheme_id and not partner.commercial_partner_id.tax_scheme_id:
			err.append(_('Invalid tax scheme for partner {0}').format(partner.name or ''))
		
		return err
