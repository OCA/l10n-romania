# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    def _compute_account_id(self):
        # For Romania, we need to set the account based on the stock
        # move accounts, if the product is storable and if the move is
        # linked to a stock move.
        res = super()._compute_account_id()
        ro_lines = self.filtered(
            lambda line: line.product_id.is_storable and line.move_id.is_l10n_ro_record
        )
        for line in ro_lines:
            stock_move = line._get_stock_moves().filtered(lambda m: m.state == "done")
            if len(stock_move) > 1:
                stock_move = stock_move[-1]
            account = line.account_id
            if stock_move:
                move_type = stock_move.l10n_ro_move_type
                if not move_type:
                    move_type = stock_move._get_l10n_ro_move_type()
                product = line.product_id.with_context(l10n_ro_stock_move=stock_move)
                accounts = product.product_tmpl_id.get_product_accounts()
                ro_account = line._get_l10n_ro_line_account(
                    stock_move, line.product_id, accounts
                )
                if ro_account and ro_account != account:
                    account = ro_account
                    line.account_id = account
        return res

    def _l10n_ro_notice_receipt_amounts(self):
        """Amounts credited to the 408 pivot by the notice receptions behind
        this bill line.

        Returns `(value, value_currency, currency, quantity)`. The lines are
        looked up on this bill line's own account, so a warehouse fiscal
        position that remaps 408 is respected. Signs are kept, so a return
        (storno entry) yields negative amounts and the same formula applies
        on a refund.
        """
        self.ensure_one()
        value = value_currency = qty = 0.0
        currency = self.company_id.currency_id
        for stock_move in self._get_stock_moves():
            if not (stock_move.l10n_ro_move_type or "").startswith("reception_notice"):
                continue
            pivot_lines = stock_move.account_move_id.line_ids.filtered(
                lambda line: line.account_id == self.account_id
            )
            if not pivot_lines:
                continue
            # 408 is credited on reception, so flip the sign to get the received value
            value -= sum(pivot_lines.mapped("balance"))
            value_currency -= sum(pivot_lines.mapped("amount_currency"))
            if pivot_lines[:1].currency_id:
                currency = pivot_lines[:1].currency_id
            qty += stock_move._get_valued_qty()
        return value, value_currency, currency, qty

    def _l10n_ro_notice_settlement_amounts(self):
        """Split the gap between this bill line and the 408 pivot in two.

        Returns `(price_difference, rate_difference)`, both in company currency,
        or `(0, 0)` when the line is not settling a reception on notice.

        The pivot was credited at the reception rate. The bill line debits it at
        the invoice rate, and the rate difference below closes the rate part, so
        whatever is left on 408 afterwards is, by construction, the price
        difference:

            residual = balance + rate_difference - value_received

        It is computed analytically rather than read back from the posted
        balance, so it is available before posting (the price difference
        confirmation dialog needs it) and it stays correct on partial invoicing.
        """
        self.ensure_one()
        company_currency = self.company_id.currency_id
        value, value_currency, currency, qty = self._l10n_ro_notice_receipt_amounts()
        if not qty:
            return 0.0, 0.0
        billed_qty = self.product_uom_id._compute_quantity(
            self.quantity, self.product_id.uom_id
        )
        # 408 is settled only for the quantity actually received; anything
        # invoiced beyond it is a price difference, never a rate difference
        ratio = min(abs(billed_qty), abs(qty)) / abs(qty)
        expected_value = company_currency.round(value * ratio)
        in_currency = (
            currency != company_currency
            and currency == self.currency_id
            and bool(self.amount_currency)
        )
        if in_currency:
            expected_currency = currency.round(value_currency * ratio)
            bill_rate = self.balance / self.amount_currency
            covered_at_bill_rate = company_currency.round(expected_currency * bill_rate)
        else:
            covered_at_bill_rate = expected_value
        rate_diff = company_currency.round(expected_value - covered_at_bill_rate)
        price_diff = company_currency.round(self.balance - covered_at_bill_rate)
        return price_diff, rate_diff

    def _l10n_ro_notice_rate_difference(self):
        """The exchange rate difference due on the 408 pivot when this bill
        line arrives: the part of the estimated liability already received,
        valued at the reception rate minus the same amount valued at the
        invoice rate. Positive is favourable (765), negative unfavourable
        (665). Zero for purchases in company currency."""
        self.ensure_one()
        return self._l10n_ro_notice_settlement_amounts()[1]

    def _l10n_ro_notice_price_difference(self):
        """The price difference left on the 408 pivot once the rate difference
        is recognised: the amount invoiced beyond what was received, valued at
        the invoice rate. This is what `l10n_ro_stock_price_difference`
        capitalises, so the pivot closes."""
        self.ensure_one()
        return self._l10n_ro_notice_settlement_amounts()[0]

    def _l10n_ro_rate_difference_line_vals(self, rate_diff):
        """The balanced pair booking the exchange rate difference:
        `Dr 408 / Cr 765` when favourable, `Cr 408 / Dr 665` when
        unfavourable. Currency neutral - an exchange rate difference exists
        only in company currency."""
        self.ensure_one()
        company = self.company_id
        exchange_account = (
            company.income_currency_exchange_account_id
            if rate_diff > 0
            else company.expense_currency_exchange_account_id
        )
        if not exchange_account:
            return []
        label = self.env._("Currency exchange rate difference")
        common = {
            "move_id": self.move_id.id,
            "name": label,
            "product_id": self.product_id.id,
            "product_uom_id": self.product_uom_id.id,
            "quantity": 0.0,
            "currency_id": self.currency_id.id,
            "amount_currency": 0.0,
            "analytic_distribution": self.analytic_distribution,
            "display_type": "cogs",
            "tax_ids": [],
        }
        return [
            dict(common, account_id=self.account_id.id, balance=rate_diff),
            dict(common, account_id=exchange_account.id, balance=-rate_diff),
        ]

    def _get_l10n_ro_line_account(self, stock_move, product, accounts):
        self.ensure_one()
        if self.move_id.is_purchase_document():
            if product.is_storable:
                account = accounts["stock_valuation"]
                if stock_move.l10n_ro_move_type in (
                    "reception_notice",
                    "reception_notice_return",
                ):
                    if accounts.get("l10n_ro_picking_payable"):
                        account = accounts["l10n_ro_picking_payable"]
                if stock_move.l10n_ro_move_type in (
                    "reception_in_progress",
                    "reception_in_progress_return",
                ):
                    if accounts.get("l10n_ro_reception_in_progress"):
                        account = accounts["l10n_ro_reception_in_progress"]
            else:
                account = accounts["expense"]
        elif self.move_id.is_sale_document():
            account = accounts["income"]
            if stock_move.l10n_ro_move_type in (
                "delivery_notice",
                "delivery_notice_return",
            ):
                if accounts.get("l10n_ro_picking_receivable"):
                    account = accounts["l10n_ro_picking_receivable"]
        return account
