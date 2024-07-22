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

    @api.model
    def _compute_taxes_for_single_line(
        self,
        base_line,
        handle_price_include=True,
        include_caba_tags=False,
        early_pay_discount_computation=None,
        early_pay_discount_percentage=None,
    ):
        move_line_account = base_line.get("account")
        if move_line_account:
            base_line["extra_context"]["l10n_ro_account_id"] = move_line_account
        return super()._compute_taxes_for_single_line(
            base_line,
            handle_price_include=handle_price_include,
            include_caba_tags=include_caba_tags,
            early_pay_discount_computation=early_pay_discount_computation,
            early_pay_discount_percentage=early_pay_discount_percentage,
        )

    @api.model
    def _convert_to_tax_line_dict(
        self,
        tax_line,
        partner=None,
        currency=None,
        taxes=None,
        tax_tags=None,
        tax_repartition_line=None,
        group_tax=None,
        account=None,
        analytic_distribution=None,
        tax_amount=None,
    ):
        res = super()._convert_to_tax_line_dict(
            tax_line,
            partner=partner,
            currency=currency,
            taxes=taxes,
            tax_tags=tax_tags,
            tax_repartition_line=tax_repartition_line,
            group_tax=group_tax,
            account=account,
            analytic_distribution=analytic_distribution,
            tax_amount=tax_amount,
        )
        if (
            tax_repartition_line
            and tax_repartition_line.l10n_ro_nondeductible
            and not tax_repartition_line.account_id
        ):
            if (
                account
                and account.company_id.l10n_ro_nondeductible_account_id
                and tax_repartition_line.l10n_ro_use_tax_exigibility_account
            ):
                res["account"] = account.company_id.l10n_ro_nondeductible_account_id
            if (
                account
                and account.l10n_ro_nondeductible_account_id
                and not tax_repartition_line.l10n_ro_use_tax_exigibility_account
            ):
                res["account"] = account.l10n_ro_nondeductible_account_id
        return res
