# ©  2020 Terrabit
# See README.rst file on addons root folder for license details

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class AccountPaymentCheck(models.AbstractModel):
    _name = "l10n.ro.mixin.payment.check"
    _description = "Account Payment Check"

    def check_amount_payment(self, payment):
        get_param = self.env["ir.config_parameter"].sudo().get_param
        amount_company_limit = get_param(
            "l10n_ro_accounting.amount_company_limit", "5000"
        )
        amount_person_limit = get_param(
            "l10n_ro_accounting.amount_person_limit", "10000"
        )
        amount_company_limit = safe_eval(amount_company_limit)
        amount_person_limit = safe_eval(amount_person_limit)

        if (
            payment.is_l10n_ro_record
            and payment.payment_type == "inbound"
            and payment.partner_type == "customer"
            and payment.journal_id.type == "cash"
        ):
            if payment.partner_id.is_company:
                if payment.amount > amount_company_limit:
                    raise ValidationError(
                        _(
                            "The payment amount (%(amount)s) cannot be greater than %(amount_limit)s",  # noqa E501
                            amount=payment.amount,
                            amount_limit=amount_company_limit,
                        )
                    )
            else:
                if payment.amount > amount_person_limit:
                    raise ValidationError(
                        _(
                            "The payment amount (%(amount)s) cannot be greater than %(amount_limit)s",  # noqa E501
                            amount=payment.amount,
                            amount_limit=amount_person_limit,
                        )
                    )

    def _check_amount(self):
        for payment in self:
            self.check_amount_payment(payment)


class AccountPaymentRegister(models.TransientModel):
    _name = "account.payment.register"
    _inherit = [
        "account.payment.register",
        "l10n.ro.mixin",
        "l10n.ro.mixin.payment.check",
    ]

    def action_create_payments(self):
        self._check_amount()
        return super().action_create_payments()


class AccountPayment(models.Model):
    _name = "account.payment"
    _inherit = ["account.payment", "l10n.ro.mixin", "l10n.ro.mixin.payment.check"]

    @api.onchange("amount", "payment_type", "partner_type", "journal_id")
    def _onchange_amount(self):
        self._check_amount()

    def write(self, vals):
        res = super().write(vals)
        if "amount" in vals:
            self._check_amount()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        payments = super().create(vals_list)
        payments._check_amount()
        return payments
