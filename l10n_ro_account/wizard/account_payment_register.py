from odoo import models


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
