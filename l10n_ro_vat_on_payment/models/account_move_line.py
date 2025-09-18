# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import date

from odoo import api, models


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    def _add_exchange_difference_cash_basis_vals(self, exchange_diff_vals):
        """For Romanian we don't do any exchange difference for cash basis"""
        not_ro_lines = self.filtered(lambda line: not line.is_l10n_ro_record)
        return super(
            AccountMoveLine, not_ro_lines
        )._add_exchange_difference_cash_basis_vals(exchange_diff_vals)

    @api.onchange("tax_ids")
    def onchange_l10n_ro_tax_ids(self):
        if self.is_l10n_ro_record:
            if "in" in self.move_id.move_type:
                partner = (
                    self.env["res.partner"]._find_accounting_partner(self.partner_id)
                    or self.partner_id
                )
                ctx = dict(self._context)
                vatp = False

                if self.move_id.invoice_date:
                    ctx.update({"check_date": self.move_id.invoice_date})
                else:
                    ctx.update({"check_date": date.today()})

                if partner:
                    vatp = partner.with_context(**ctx)._check_vat_on_payment()

                if vatp:
                    taxes = self.tax_ids

                    if taxes and self.move_id.fiscal_position_id:
                        taxes = self.move_id.fiscal_position_id.map_tax(taxes)

                    self.tax_ids = taxes
