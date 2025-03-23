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

    @api.depends("product_id", "product_uom_id", "account_id")
    def _compute_tax_ids(self):
        res = super()._compute_tax_ids()
        ro_lines = self.filtered(lambda line: line.is_l10n_ro_record)
        for line in ro_lines:
            if not line.product_id and line.account_id:
                line.tax_ids = line._get_computed_taxes()
        return res

    def _get_computed_taxes(self):
        self.ensure_one()
        res = super()._get_computed_taxes()
        if self.is_l10n_ro_record and not res:
            if self.move_id.is_sale_document(include_receipts=True):
                res = self.company_id.l10n_ro_account_serv_sale_tax_id
            elif self.move_id.is_purchase_document(include_receipts=True):
                res = self.company_id.l10n_ro_account_serv_purchase_tax_id
            if res and self.move_id.fiscal_position_id:
                res = self.move_id.fiscal_position_id.map_tax(res)
        return res

    @api.onchange("tax_ids")
    def onchange_l10n_ro_tax_ids(self):
        taxes = self.tax_ids or self._origin.tax_ids
        if self.is_l10n_ro_record and taxes:
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
                    if taxes and self.move_id.fiscal_position_id:
                        taxes = self.move_id.fiscal_position_id.map_tax(taxes)

                    self.tax_ids = taxes
