# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountTaxExtend(models.Model):
    _name = "account.tax"
    _inherit = ["account.tax", "l10n.ro.mixin"]

    l10n_ro_nondeductible_tax_id = fields.Many2one(
        "account.tax", copy=False, string="Romania - Nondeductible Tax"
    )
    l10n_ro_is_nondeductible = fields.Boolean(
        string="Romania - Is Nondeductible",
        compute="_compute_boolean_l10n_ro_nondeductible",
        store=True,
    )

    @api.depends("invoice_repartition_line_ids", "refund_repartition_line_ids")
    def _compute_boolean_l10n_ro_nondeductible(self):
        for record in self:
            if record.is_l10n_ro_record:
                record.l10n_ro_is_nondeductible = any(
                    record.invoice_repartition_line_ids.mapped("l10n_ro_nondeductible")
                    + record.refund_repartition_line_ids.mapped("l10n_ro_nondeductible")
                )
            else:
                record.l10n_ro_is_nondeductible = False


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
