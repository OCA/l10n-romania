# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models
from odoo.fields import Domain


class PosSession(models.Model):
    _inherit = "pos.session"

    def _get_captured_payments_domain(self):
        # The cash of a refund leaves the till through its payment disposal
        # statement line, which the session already counts; counting the POS
        # payment on top of it would take the money out twice.
        return Domain.AND(
            [
                super()._get_captured_payments_domain(),
                [("l10n_ro_payment_disposal_id", "=", False)],
            ]
        )

    def _l10n_ro_get_disposed_payments(self):
        """Payments of this session already carried by a payment disposal."""
        return self._get_closed_orders().payment_ids.filtered(
            "l10n_ro_payment_disposal_id"
        )

    def get_closing_control_data(self):
        data = super().get_closing_control_data()
        cash_details = data.get("default_cash_details")
        if not cash_details:
            return data
        # Unlike the cash balance, the closing control sums the POS payments
        # itself instead of going through _get_captured_payments_domain.
        disposed = sum(
            self._l10n_ro_get_disposed_payments()
            .filtered(
                lambda payment: payment.payment_method_id.id == cash_details.get("id")
            )
            .mapped("amount")
        )
        if disposed:
            cash_details["amount"] -= disposed
            cash_details["payment_amount"] -= disposed
        return data
