import logging

from lxml import etree

from openerp import api, fields, models, _
from openerp.exceptions import UserError

logger = logging.getLogger(__name__)


class BaseUbl(models.AbstractModel):
	_inherit = "base.ubl"

	@api.model
	def _ubl_add_payment_means(
		self,
		partner_bank,
		payment_mode,
		date_due,
		parent_node,
		ns,
		payment_identifier=None,
		version="2.1",
	):
		pay_means = etree.SubElement(parent_node, ns["cac"] + "PaymentMeans")
		pay_means_code = etree.SubElement(
			pay_means, ns["cbc"] + "PaymentMeansCode"
		)
		# Why not schemeAgencyID='6' + schemeID
		if payment_mode and hasattr(payment_mode, "unece_id") and hasattr(payment_mode, "unece_code"):  # type is a required field on payment_mode
			if not payment_mode.unece_id:
				raise UserError(_("Missing 'UNECE Payment Mean' on payment mode '{0}' ").format(payment_mode.name or ''))
			pay_means_code.text = payment_mode.unece_code
		else:
			pay_means_code.text = "31"
			logger.warning(
				"Missing payment mode on invoice ID %d. "
				"Using 31 (wire transfer) as UNECE code as fallback "
				"for payment mean",
				self.id,
			)
		
		if pay_means_code.text in ["30", "31", "42"] and partner_bank:
			# In the Chorus specs, they except 'IBAN' in PaymentChannelCode
			# I don't know if this usage is common or nots
			
			if payment_identifier:
				payment_id = etree.SubElement(pay_means, ns["cbc"] + "PaymentID")
				payment_id.text = payment_identifier
			payee_fin_account = etree.SubElement(
				pay_means, ns["cac"] + "PayeeFinancialAccount"
			)
			payee_fin_account_id = etree.SubElement(
				payee_fin_account, ns["cbc"] + "ID"
			)
			payee_fin_account_id.text = partner_bank.sanitized_acc_number
			if partner_bank.bank_bic:
				financial_inst_branch = etree.SubElement(
					payee_fin_account, ns["cac"] + "FinancialInstitutionBranch"
				)				
