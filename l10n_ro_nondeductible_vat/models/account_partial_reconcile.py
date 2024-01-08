from odoo import api, models


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    @api.model
    def _prepare_cash_basis_tax_line_vals(self, tax_line, balance, amount_currency):
        vals = super()._prepare_cash_basis_tax_line_vals(
            tax_line, balance, amount_currency
        )
        if (
            tax_line.tax_repartition_line_id.skip_cash_basis_account_switch
            and tax_line.company_id.account_cash_basis_base_account_id
        ):
            vals[
                "account_id"
            ] = tax_line.company_id.account_cash_basis_base_account_id.id
        return vals

    @api.model
    def _prepare_cash_basis_counterpart_tax_line_vals(self, tax_line, cb_tax_line_vals):
        vals = super()._prepare_cash_basis_counterpart_tax_line_vals(
            tax_line, cb_tax_line_vals
        )
        if (
            tax_line.tax_repartition_line_id.skip_cash_basis_account_switch
            and tax_line.company_id.account_cash_basis_base_account_id
        ):
            vals[
                "account_id"
            ] = tax_line.company_id.account_cash_basis_base_account_id.id
        return vals
