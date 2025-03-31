# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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

    l10n_ro_negative_allow = fields.Boolean(
        string="Allow negative tax",
        help="Allows negative tax repartition in tax per account.",
        default=False,
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

    @api.depends(
        "invoice_repartition_line_ids.factor",
        "invoice_repartition_line_ids.repartition_type",
    )
    def _compute_has_negative_factor(self):
        for tax in self:
            if tax.l10n_ro_negative_allow is False:
                tax_reps = tax.invoice_repartition_line_ids.filtered(
                    lambda x: x.repartition_type == "tax"
                )
                tax.has_negative_factor = bool(
                    tax_reps.filtered(lambda tax_rep: tax_rep.factor < 0.0)
                )
            else:
                tax.has_negative_factor = False

    # pylint: disable=W8110
    @api.constrains(
        "invoice_repartition_line_ids",
        "refund_repartition_line_ids",
        "repartition_line_ids",
    )
    def _validate_repartition_lines(self):
        if self.env.company.l10n_ro_accounting:
            for record in self:
                # if the tax is an aggregation of its sub-taxes (group) it can
                # have no repartition lines
                if (
                    record.amount_type == "group"
                    and not record.invoice_repartition_line_ids
                    and not record.refund_repartition_line_ids
                ):
                    continue

                invoice_repartition_line_ids = (
                    record.invoice_repartition_line_ids.sorted(
                        lambda line: (line.sequence, line.id)
                    )
                )
                refund_repartition_line_ids = record.refund_repartition_line_ids.sorted(
                    lambda line: (line.sequence, line.id)
                )
                record._check_repartition_lines(invoice_repartition_line_ids)
                record._check_repartition_lines(refund_repartition_line_ids)

                if len(invoice_repartition_line_ids) != len(
                    refund_repartition_line_ids
                ):
                    raise ValidationError(
                        _(
                            "Invoice and credit note distribution should have the"
                            " same number of lines."
                        )
                    )

                if not invoice_repartition_line_ids.filtered(
                    lambda x: x.repartition_type == "tax"
                ) or not refund_repartition_line_ids.filtered(
                    lambda x: x.repartition_type == "tax"
                ):
                    raise ValidationError(
                        _(
                            "Invoice and credit note repartition should have at least"
                            " one tax repartition line."
                        )
                    )

                index = 0
                while index < len(invoice_repartition_line_ids):
                    inv_rep_ln = invoice_repartition_line_ids[index]
                    ref_rep_ln = refund_repartition_line_ids[index]
                    if (
                        inv_rep_ln.repartition_type != ref_rep_ln.repartition_type
                        or inv_rep_ln.factor_percent != ref_rep_ln.factor_percent
                    ):
                        raise ValidationError(
                            _(
                                "Invoice and credit note distribution should match"
                                "same percentages."
                            )
                        )
                    index += 1

        else:
            super()._validate_repartition_lines()

    # flake8: noqa: C901
    @api.model
    def _add_accounting_data_to_base_line_tax_details(
        self, base_line, company, include_caba_tags=False
    ):
        if self.env.company.l10n_ro_accounting:
            is_refund = base_line["is_refund"]
            currency = base_line["currency_id"] or company.currency_id
            product = base_line["product_id"]
            company_currency = company.currency_id
            if is_refund:
                repartition_lines_field = "refund_repartition_line_ids"
            else:
                repartition_lines_field = "invoice_repartition_line_ids"

            # Tags on the base line.
            taxes_data = base_line["tax_details"]["taxes_data"]
            base_line["tax_tag_ids"] = self.env["account.account.tag"]
            if product:
                countries = {tax_data["tax"].country_id for tax_data in taxes_data}
                countries.add(False)
                base_line["tax_tag_ids"] |= product.sudo().account_tag_ids

            for tax_data in taxes_data:
                tax = tax_data["tax"]

                # Tags on the base line.
                if not tax_data["is_reverse_charge"] and (
                    include_caba_tags or tax.tax_exigibility == "on_invoice"
                ):
                    base_line["tax_tag_ids"] |= (
                        tax[repartition_lines_field]
                        .filtered(lambda x: x.repartition_type == "base")
                        .tag_ids
                    )

                # Compute repartition lines amounts.
                if tax.l10n_ro_negative_allow:
                    tax_reps = tax[repartition_lines_field].filtered(
                        lambda x: x.repartition_type == "tax"
                    )
                    tax_rep_sign = 1.0
                else:
                    if tax_data["is_reverse_charge"]:
                        tax_reps = tax[repartition_lines_field].filtered(
                            lambda x: x.repartition_type == "tax" and x.factor < 0.0
                        )
                        tax_rep_sign = -1.0
                    else:
                        tax_reps = tax[repartition_lines_field].filtered(
                            lambda x: x.repartition_type == "tax" and x.factor >= 0.0
                        )
                        tax_rep_sign = 1.0

                total_tax_rep_amounts = {
                    "tax_amount_currency": 0.0,
                    "tax_amount": 0.0,
                }
                tax_reps_data = tax_data["tax_reps_data"] = []
                for tax_rep in tax_reps:
                    tax_amount_currency = tax_data.get("tax_amount_currency")

                    if self.env.context.get("compute_all_use_raw_base_lines"):
                        tax_amount_currency = tax_data.get("raw_tax_amount_currency")

                    tax_rep_data = {
                        "tax_rep": tax_rep,
                        "tax_amount_currency": currency.round(
                            tax_amount_currency * tax_rep.factor * tax_rep_sign
                        ),
                        "tax_amount": currency.round(
                            tax_data["tax_amount"] * tax_rep.factor * tax_rep_sign
                        ),
                        "account": tax_rep._get_aml_target_tax_account(
                            force_caba_exigibility=include_caba_tags
                        )
                        or base_line["account_id"],
                    }
                    total_tax_rep_amounts["tax_amount_currency"] += tax_rep_data[
                        "tax_amount_currency"
                    ]
                    total_tax_rep_amounts["tax_amount"] += tax_rep_data["tax_amount"]
                    tax_reps_data.append(tax_rep_data)

                # Distribute the delta on the repartition lines.
                sorted_tax_reps_data = sorted(
                    tax_reps_data,
                    key=lambda tax_rep: (
                        -abs(tax_rep["tax_amount_currency"]),
                        -abs(tax_rep["tax_amount"]),
                    ),
                )
                for field, field_currency in (
                    ("tax_amount_currency", currency),
                    ("tax_amount", company_currency),
                ):
                    tax_amount = tax_data.get(field)
                    if self.env.context.get("compute_all_use_raw_base_lines"):
                        tax_amount = tax_data.get(f"raw_{field}")
                    total_error = tax_amount - total_tax_rep_amounts[field]
                    nb_of_errors = round(abs(total_error / field_currency.rounding))
                    if not nb_of_errors:
                        continue

                    amount_to_distribute = total_error / nb_of_errors
                    index = 0
                    while nb_of_errors:
                        tax_rep = sorted_tax_reps_data[index]
                        tax_rep[field] += amount_to_distribute
                        nb_of_errors -= 1
                        index = (index + 1) % len(sorted_tax_reps_data)

            subsequent_taxes = self.env["account.tax"]
            subsequent_tags_per_tax = defaultdict(
                lambda: self.env["account.account.tag"]
            )
            for tax_data in reversed(taxes_data):
                tax = tax_data["tax"]

                for tax_rep_data in tax_data["tax_reps_data"]:
                    tax_rep = tax_rep_data["tax_rep"]

                    # Compute subsequent taxes/tags.
                    tax_rep_data["taxes"] = self.env["account.tax"]
                    tax_rep_data["tax_tags"] = self.env["account.account.tag"]
                    if include_caba_tags or tax.tax_exigibility == "on_invoice":
                        tax_rep_data["tax_tags"] = tax_rep.tag_ids
                    if tax.include_base_amount:
                        tax_rep_data["taxes"] |= subsequent_taxes
                        for other_tax, tags in subsequent_tags_per_tax.items():
                            if tax != other_tax:
                                tax_rep_data["tax_tags"] |= tags

                    # Add the accounting grouping_key to create the tax lines.
                    base_line_grouping_key = self._prepare_base_line_grouping_key(
                        base_line
                    )
                    tax_rep_data["grouping_key"] = (
                        self._prepare_base_line_tax_repartition_grouping_key(
                            base_line,
                            base_line_grouping_key,
                            tax_data,
                            tax_rep_data,
                        )
                    )

                if tax.is_base_affected:
                    subsequent_taxes |= tax
                    if include_caba_tags or tax.tax_exigibility == "on_invoice":
                        subsequent_tags_per_tax[tax] |= (
                            tax[repartition_lines_field]
                            .filtered(lambda x: x.repartition_type == "base")
                            .tag_ids
                        )
        else:
            super()._add_accounting_data_to_base_line_tax_details(
                base_line, company, include_caba_tags=False
            )
