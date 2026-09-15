# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class PosPayment(models.Model):
    _inherit = "pos.payment"

    l10n_ro_payment_disposal_id = fields.Many2one(
        "account.bank.statement.line",
        string="Romania - Payment Disposal",
        readonly=True,
        copy=False,
        help="Cash statement line that paid this refund out of the till.",
    )

    def _l10n_ro_payment_disposals(self):
        """Payments settled by a payment disposal instead of the POS cash flow.

        The money leaves the till against a signed "dispozitie de plata", so
        these payments get their own statement line and must be kept out of
        every place where core would count the POS payment itself.
        """
        return self.filtered(
            lambda payment: payment.payment_method_id.type == "cash"
            and payment.pos_order_id._l10n_ro_is_refund_order()
        )
