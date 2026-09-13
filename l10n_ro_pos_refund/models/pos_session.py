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

    def _accumulate_amounts(self, data):
        data = super()._accumulate_amounts(data)
        for payment in self._l10n_ro_get_disposed_payments():
            split = payment.payment_method_id.split_transactions
            key = payment if split else payment.payment_method_id
            # The statement line already credits the till and debits the
            # customer, so the closing entry must carry neither side.
            self._l10n_ro_deduct_amounts(
                data["split_receivables_cash" if split else "combine_receivables_cash"],
                key,
                payment.amount,
                payment.payment_date,
            )
            self._l10n_ro_deduct_amounts(
                data[
                    "split_invoice_receivables"
                    if split
                    else "combine_invoice_receivables"
                ],
                key,
                payment.amount,
                payment.pos_order_id.date_order,
            )
        return data

    def _l10n_ro_deduct_amounts(self, amounts_by_key, key, amount, date):
        """Take ``amount`` back out of an accumulated bucket, dropping the key
        when nothing is left -- core creates a move line for every key it
        finds, zero amount included."""
        if key not in amounts_by_key:
            return
        amounts = self._update_amounts(amounts_by_key[key], {"amount": -amount}, date)
        if self.currency_id.is_zero(
            amounts["amount"]
        ) and self.company_id.currency_id.is_zero(amounts["amount_converted"]):
            del amounts_by_key[key]
        else:
            amounts_by_key[key] = amounts
