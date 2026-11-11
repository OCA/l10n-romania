# Copyright 2018 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models
from odoo.tools import float_compare

L10N_RO_RATE_DIGITS = 4


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    l10n_ro_currency_rate = fields.Float(
        string="Romania - Currency Rate",
        compute="_compute_l10n_ro_currency_rate",
        inverse="_inverse_l10n_ro_currency_rate",
        digits=(12, L10N_RO_RATE_DIGITS),
        help="1 document currency = X company currency. "
        "Inverse of the standard Currency Rate, changing one updates the other.",
    )

    def _get_l10n_ro_currency_rate(self):
        self.ensure_one()
        rate = self.invoice_currency_rate
        return 1 / rate if rate else 1.0

    @api.depends("invoice_currency_rate")
    def _compute_l10n_ro_currency_rate(self):
        for move in self:
            move.l10n_ro_currency_rate = move._get_l10n_ro_currency_rate()

    def _inverse_l10n_ro_currency_rate(self):
        for move in self:
            rate = move.l10n_ro_currency_rate
            if rate <= 0:
                continue
            # Only write when the user really changed the RO rate: the RO
            # field is rounded to 4 digits, rewriting the standard rate from
            # it every time would alter a more precise manual standard rate.
            if (
                float_compare(
                    rate,
                    move._get_l10n_ro_currency_rate(),
                    precision_digits=L10N_RO_RATE_DIGITS,
                )
                != 0
            ):
                move.invoice_currency_rate = 1 / rate

    @api.onchange("l10n_ro_currency_rate")
    def _onchange_l10n_ro_currency_rate(self):
        # Inverses run only on save, apply it in the form too so that the
        # standard rate and the lines are updated before saving.
        for move in self:
            if move.l10n_ro_currency_rate <= 0:
                move.l10n_ro_currency_rate = move._get_l10n_ro_currency_rate()
        self._inverse_l10n_ro_currency_rate()
