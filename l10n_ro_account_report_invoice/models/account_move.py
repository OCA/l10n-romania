# Copyright 2018 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    @api.depends("currency_id", "invoice_date")
    def _compute_l10n_ro_currency_rate(self):
        for invoice in self:
            currency_rate = 1
            if invoice.is_l10n_ro_record and invoice.currency_id:
                currency_rate = self.env["res.currency"]._get_conversion_rate(
                    invoice.currency_id,
                    invoice.company_currency_id,
                    invoice.company_id or self.env.company,
                    invoice.invoice_date or fields.Date.today(),
                )
            invoice.l10n_ro_currency_rate = currency_rate

    l10n_ro_currency_rate = fields.Float(
        string="Romania - Currency Rate",
        store=True,
        readonly=True,
        compute="_compute_l10n_ro_currency_rate",
    )
