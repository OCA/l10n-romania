# Copyright 2024 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    def _create_exchange_difference_move(self, exchange_diff_vals):
        """Inherit Odoo method to not do exchange differences for
        invoices with the same currency as company
        """
        if not self:
            return self.env["account.move"]
        company_currency = self[0].company_id.currency_id
        currency_lines = self.filtered(
            lambda l: l.is_l10n_ro_record and l.currency_id == company_currency
        )
        return super(
            AccountMoveLine, self - currency_lines
        )._create_exchange_difference_move(exchange_diff_vals)
