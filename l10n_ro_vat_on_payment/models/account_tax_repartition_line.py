# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountTaxRepartitionLine(models.Model):
    _name = "account.tax.repartition.line"
    _inherit = ["account.tax.repartition.line", "l10n.ro.mixin"]

    l10n_ro_skip_cash_basis_account_switch = fields.Boolean(
        string="Romania - Skip Account Switch (Cash Basis)",
        help="If checked, then it doesn't change expense account"
        " in the tax line for invoices, and it set 44283 instead of expense"
        " account for the journal entry created at payment reconciliation",
    )

    def _get_aml_target_tax_account(self, force_caba_exigibility=False):
        """Get the default tax account to set on a business line.

        :return: An account.account record or an empty recordset.
        """
        self.ensure_one()
        res = super(AccountTaxRepartitionLine, self)._get_aml_target_tax_account(
            force_caba_exigibility=force_caba_exigibility
        )
        account = False
        if (
            self.company_id.country_id.code == "RO"
            and self.tax_id.tax_exigibility == "on_payment"
        ):
            account = self.tax_id.cash_basis_transition_account_id
        if (
            not force_caba_exigibility
            and self.tax_id.tax_exigibility == "on_payment"
            and not self._context.get("caba_no_transition_account")
            and not self.l10n_ro_skip_cash_basis_account_switch
        ):
            account = self.tax_id.cash_basis_transition_account_id
        if not account:
            account = res
        return account
