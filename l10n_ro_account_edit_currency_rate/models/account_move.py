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

    @api.onchange("l10n_ro_currency_rate")
    def onchange_l10n_ro_currency_rate(self):
        if self.is_l10n_ro_record:
            self = self.with_context(
                l10n_ro_force_currency_rate=self.l10n_ro_currency_rate
            )
        self.line_ids._compute_currency_rate()
        self.line_ids._inverse_amount_currency()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends("currency_id", "company_id", "move_id.date")
    def _compute_currency_rate(self):
        res = super()._compute_currency_rate()
        for line in self:
            if line.move_id.is_l10n_ro_record and self._context.get(
                "l10n_ro_force_currency_rate"
            ):
                line.currency_rate = 1 / line.move_id.l10n_ro_currency_rate
        return res

    @api.onchange("amount_currency", "currency_id", "currency_rate")
    def _inverse_amount_currency(self):
        res = super()._inverse_amount_currency()
        for line in self:
            if (
                line.currency_id != line.company_id.currency_id
                and line.move_id.is_l10n_ro_record
                and self._context.get("l10n_ro_force_currency_rate")
            ):
                line.balance = line.company_id.currency_id.round(
                    line.amount_currency / line.currency_rate
                )
        return res
