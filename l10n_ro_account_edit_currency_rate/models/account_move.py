# Copyright 2018 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class Currency(models.Model):
    _inherit = "res.currency"

    # pylint: disable=W0622
    def _convert(self, from_amount, to_currency, company, date, round=True):
        if self._context.get("l10n_ro_force_currency_rate"):
            self, to_currency = self or to_currency, to_currency or self
            assert self, "convert amount from unknown currency"
            assert to_currency, "convert amount to unknown currency"
            assert company, "convert amount from unknown company"
            assert date, "convert amount from unknown date"

            if self == to_currency:
                to_amount = from_amount
            else:
                to_amount = from_amount * self._context["l10n_ro_force_currency_rate"]
            return to_currency.round(to_amount) if round else to_amount

        return super()._convert(from_amount, to_currency, company, date, round=round)


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ro_currency_rate = fields.Float(
        string="Romania - Currency Rate", readonly=False
    )

    def _update_context_with_currency_rate(self, context_record=None):
        if context_record is None:
            context_record = self
        if self.currency_id:
            default_currency_rate = self.env["res.currency"]._get_conversion_rate(
                self.currency_id,
                self.company_currency_id,
                self.company_id or self.env.company,
                self.invoice_date or fields.Date.today(),
            )
            if self.l10n_ro_currency_rate != default_currency_rate:
                return context_record.with_context(
                    l10n_ro_force_currency_rate=self.l10n_ro_currency_rate
                )
        return context_record

    @api.onchange("l10n_ro_currency_rate")
    def onchange_l10n_ro_currency_rate(self):
        self = self.with_context(l10n_ro_force_currency_rate=self.l10n_ro_currency_rate)
        self.line_ids._onchange_amount_currency()

    def _recompute_dynamic_lines(
        self, recompute_all_taxes=False, recompute_tax_base_amount=False
    ):
        self = self._update_context_with_currency_rate()
        super()._recompute_dynamic_lines(
            recompute_all_taxes=recompute_all_taxes,
            recompute_tax_base_amount=recompute_tax_base_amount,
        )


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange("quantity", "discount", "price_unit", "tax_ids")
    def _onchange_price_subtotal(self):
        self = self.move_id._update_context_with_currency_rate(context_record=self)
        return super(AccountMoveLine, self)._onchange_price_subtotal()

    @api.onchange("amount_currency")
    def _onchange_amount_currency(self):
        self = self.move_id._update_context_with_currency_rate(context_record=self)
        return super(AccountMoveLine, self)._onchange_amount_currency()
