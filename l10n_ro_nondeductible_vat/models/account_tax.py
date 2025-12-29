# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.fields import Command


class AccountTax(models.Model):
    _name = "account.tax"
    _inherit = ["account.tax", "l10n.ro.mixin"]

    l10n_ro_is_nondeductible = fields.Boolean(
        string="Romania - Is Nondeductible",
        compute="_compute_is_l10n_ro_nondeductible",
        store=True,
    )

    @api.depends("repartition_line_ids.tag_ids.l10n_ro_nondeductible_tag_id")
    def _compute_is_l10n_ro_nondeductible(self):
        for record in self:
            if record.is_l10n_ro_record:
                record.l10n_ro_is_nondeductible = any(
                    record.repartition_line_ids.tag_ids.mapped(
                        "l10n_ro_nondeductible_tag_id"
                    )
                )
            else:
                record.l10n_ro_is_nondeductible = False

    @api.model
    def _prepare_tax_lines(self, base_lines, company, tax_lines=None):
        if company.l10n_ro_accounting:
            non_ded_base_lines = [
                line
                for line in base_lines
                if line.get("special_type") == "non_deductible"
            ]
            for line in non_ded_base_lines:
                tax_details = line.get("tax_details") or {}
                if tax_details.get("taxes_data", []) != []:
                    tax_details["taxes_data"] = []
        res = super()._prepare_tax_lines(base_lines, company, tax_lines=tax_lines)
        if company.l10n_ro_accounting:
            base_lines_to_update = res.get("base_lines_to_update", [])
            for base_line, vals in base_lines_to_update:
                if (
                    isinstance(base_line["record"], models.Model)
                    and base_line["record"]._name == "account.move.line"
                ):
                    aml = base_line["record"]
                    if self.env.context.get("l10n_ro_exclude_from_stock"):
                        if base_line.get("special_mode") == "total_excluded":
                            vals["tax_tag_ids"] = [Command.set([])]
                    if aml.l10n_ro_non_deductible_line_id:
                        tax = aml.l10n_ro_non_deductible_line_id.tax_ids.filtered(
                            lambda t: t.amount_type != "fixed"
                        )
                        if "refund" in aml.move_id.move_type:
                            tax_reps = tax.refund_repartition_line_ids
                        else:
                            tax_reps = tax.invoice_repartition_line_ids
                        base_rep_line = tax_reps.filtered(
                            lambda rep_line: rep_line.repartition_type == "base"
                        )
                        base_rep_tags = base_rep_line.tag_ids
                        base_nd_rep_tags = base_rep_tags.l10n_ro_nondeductible_tag_id
                        if aml.display_type == "non_deductible_product":
                            # Remove the tax
                            vals["tax_ids"] = [Command.set([])]
                            if base_rep_tags:
                                vals["tax_tag_ids"] = [Command.set(base_rep_tags.ids)]
                        if aml.display_type == "non_deductible_product_total":
                            if base_nd_rep_tags:
                                vals["tax_tag_ids"] = [
                                    Command.set(base_nd_rep_tags.ids)
                                ]
                            else:
                                vals["tax_tag_ids"] = [Command.set(base_rep_tags.ids)]
        return res

    @api.model
    def _get_tax_totals_summary(
        self, base_lines, currency, company, cash_rounding=None
    ):
        res = super()._get_tax_totals_summary(
            base_lines, currency, company, cash_rounding=cash_rounding
        )
        if company.l10n_ro_accounting and res.get("subtotals"):
            for subtotal in res["subtotals"]:
                for tax_group in subtotal["tax_groups"]:
                    if "non_deductible_tax_amount" in tax_group:
                        tax_group["l10n_ro_non_deductible_tax_amount"] = tax_group.get(
                            "non_deductible_tax_amount", 0.0
                        )
                        tax_group["l10n_ro_non_deductible_tax_amount_currency"] = (
                            tax_group.get("non_deductible_tax_amount_currency", 0.0)
                        )
                        tax_group["non_deductible_tax_amount"] = 0.0
                        tax_group["non_deductible_tax_amount_currency"] = 0.0
        return res
