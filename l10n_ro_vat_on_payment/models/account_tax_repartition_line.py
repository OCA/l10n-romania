# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountTaxRepartitionLine(models.Model):
    _inherit = "account.tax.repartition.line"

    def _get_aml_target_tax_account(self, force_caba_exigibility=False):
        """Get the default tax account to set on a business line.

        :return: An account.account record or an empty recordset.
        """
        self.ensure_one()
        res = super()._get_aml_target_tax_account(
            force_caba_exigibility=force_caba_exigibility
        )
        if (
            self.company_id.country_id.code == "RO"
            and self.tax_id.tax_exigibility == "on_payment"
        ):
            return self.tax_id.cash_basis_transition_account_id
        return res
