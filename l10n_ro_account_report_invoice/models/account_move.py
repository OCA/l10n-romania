# Copyright 2018 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends("currency_id", "invoice_date")
    def _compute_currency_rate(self):
        for invoice in self:
            if self.currency_id:
                invoice.currency_rate = self.env["res.currency"]._get_conversion_rate(
                    invoice.currency_id,
                    invoice.company_currency_id,
                    invoice.company_id or self.env.company,
                    invoice.invoice_date or fields.Date.today(),
                )

    currency_rate = fields.Float(
        string="Currency Rate",
        store=True,
        readonly=True,
        compute="_compute_currency_rate",
    )
