# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
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
                
                
                
    @api.constrains(
        "invoice_repartition_line_ids",
        "refund_repartition_line_ids",
        "repartition_line_ids",
    )
    def _validate_repartition_lines(self):
        if self.env.company.l10n_ro_accounting:
            for record in self:
                # if the tax is an aggregation of its sub-taxes (group) it can have no repartition lines
                if (
                    record.amount_type == "group"
                    and not record.invoice_repartition_line_ids
                    and not record.refund_repartition_line_ids
                ):
                    continue

                invoice_repartition_line_ids = (
                    record.invoice_repartition_line_ids.sorted(
                        lambda l: (l.sequence, l.id)
                    )
                )
                refund_repartition_line_ids = record.refund_repartition_line_ids.sorted(
                    lambda l: (l.sequence, l.id)
                )
                record._check_repartition_lines(invoice_repartition_line_ids)
                record._check_repartition_lines(refund_repartition_line_ids)

                if len(invoice_repartition_line_ids) != len(
                    refund_repartition_line_ids
                ):
                    raise ValidationError(
                        _(
                            "Invoice and credit note distribution should have the same number of lines."
                        )
                    )

                if not invoice_repartition_line_ids.filtered(
                    lambda x: x.repartition_type == "tax"
                ) or not refund_repartition_line_ids.filtered(
                    lambda x: x.repartition_type == "tax"
                ):
                    raise ValidationError(
                        _(
                            "Invoice and credit note repartition should have at least one tax repartition line."
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
                                "Invoice and credit note distribution should match (same percentages, in the same order)."
                            )
                        )
                    index += 1

        else:
            super()._validate_repartition_lines()
