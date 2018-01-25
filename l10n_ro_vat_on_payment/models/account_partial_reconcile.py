# Copyright  2015 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    def _get_tax_cash_basis_base_account(self, line, tax):
        if tax.cash_basis_base_account_id:
            return tax.cash_basis_base_account_id
        return super(
            AccountPartialReconcile, self)._get_tax_cash_basis_base_account(
                line, tax)
