# ©  2020 Terrabit
# See README.rst file on addons root folder for license details

from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountPaymentRegister(models.TransientModel):
    _name = "account.payment.register"
    _inherit = ["account.payment.register", "l10n.ro.mixin"]

    def _check_amount(self):
        for payment in self:
            if (
                payment.is_l10n_ro_record
                and payment.payment_type == "inbound"
                and payment.partner_type == "customer"
                and payment.journal_id.type == "cash"
            ):
                if payment.partner_id.is_company:
                    if payment.amount > 5000:
                        raise ValidationError(
                            _("The payment amount (%s) cannot be greater than 5000")
                            % payment.amount
                        )
                else:
                    if payment.amount > 10000:
                        raise ValidationError(
                            _("The payment amount (%s) cannot be greater than 10000")
                            % payment.amount
                        )

    def action_create_payments(self):
        self._check_amount()
        return super().action_create_payments()


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _check_amount(self):
        for payment in self:
            if (
                payment.is_l10n_ro_record
                and payment.payment_type == "inbound"
                and payment.partner_type == "customer"
                and payment.journal_id.type == "cash"
            ):
                if payment.partner_id.is_company:
                    if payment.amount > 5000:
                        raise ValidationError(
                            _("The payment amount (%s) cannot be greater than 5000")
                            % payment.amount
                        )
                else:
                    if payment.amount > 10000:
                        raise ValidationError(
                            _("The payment amount (%s) cannot be greater than 10000")
                            % payment.amount
                        )

    @api.onchange("amount", "payment_type", "partner_type", "journal_id")
    def _onchange_amount(self):
        self._check_amount()

    def write(self, vals):
        if "amount" in vals:
            self._check_amount()
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "amount" in vals:
                self._check_amount()
        return super().create(vals_list)
