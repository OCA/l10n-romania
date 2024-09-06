# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountTaxRepartitionLineExtend(models.Model):
    _name = "account.tax.repartition.line"
    _inherit = ["account.tax.repartition.line", "l10n.ro.mixin"]

    l10n_ro_nondeductible = fields.Boolean(string="Romania - Nondeductible")
    l10n_ro_exclude_from_stock = fields.Boolean(string="Romania - Exclude From Stock")
    l10n_ro_skip_cash_basis_account_switch = fields.Boolean(
        string="Romania - Skip Account Switch (Cash Basis)",
        help="If checked, then it doesn't change expense account"
        " in the tax line for invoices, and it set 44283 instead of expense"
        " account for the journal entry created at payment reconciliation",
    )

    def _get_aml_target_tax_account(self, force_caba_exigibility=False):
        if not self.tax_id.is_l10n_ro_record:
            return super()._get_aml_target_tax_account(
                force_caba_exigibility=force_caba_exigibility
            )
        account = False
        if (
            not force_caba_exigibility
            and self.tax_id.tax_exigibility == "on_payment"
            and not self._context.get("caba_no_transition_account")
            and not self.l10n_ro_skip_cash_basis_account_switch
        ):
            account = self.tax_id.cash_basis_transition_account_id
        if not account:
            account = self.account_id
        return account
