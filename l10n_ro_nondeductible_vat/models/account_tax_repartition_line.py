# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountTaxRepartitionLineExtend(models.Model):
    _name = "account.tax.repartition.line"
    _inherit = ["account.tax.repartition.line", "l10n.ro.mixin"]

    l10n_ro_nondeductible = fields.Boolean(string="Romania - Nondeductible")
    l10n_ro_use_tax_exigibility_account = fields.Boolean(
        string="Romania - Use Tax Exigibility Account"
    )
    l10n_ro_exclude_from_stock = fields.Boolean(string="Romania - Exclude From Stock")

    def _get_aml_target_tax_account(self, force_caba_exigibility=False):
        res = super()._get_aml_target_tax_account(
            force_caba_exigibility=force_caba_exigibility
        )
        if self.l10n_ro_nondeductible and not self.account_id:
            line_account = self.env.context.get("l10n_ro_account_id")
            company = self.company_id
            if (
                company.l10n_ro_nondeductible_account_id
                and self.l10n_ro_use_tax_exigibility_account
            ):
                res = company.l10n_ro_nondeductible_account_id
            if (
                line_account
                and line_account.l10n_ro_nondeductible_account_id
                and not self.l10n_ro_use_tax_exigibility_account
            ):
                res = line_account.l10n_ro_nondeductible_account_id
        return res
