# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.fields import Command
from odoo.exceptions import ValidationError


class AccountTax(models.Model):
    _name = "account.tax"
    _inherit = ["account.tax", "l10n.ro.mixin"]

    l10n_ro_nondeductible_tax_id = fields.Many2one(
        "account.tax", copy=False, string="Romania - Nondeductible Tax"
    )
    l10n_ro_is_nondeductible = fields.Boolean(
        string="Romania - Is Nondeductible",
        compute="_compute_is_l10n_ro_nondeductible",
        store=True,
    )

    l10n_ro_negative_allow = fields.Boolean(
        string="Allow negative tax",
        help="Allows negative tax repartition in tax per account.",
        default=False,
    )

    @api.depends("invoice_repartition_line_ids", "refund_repartition_line_ids")
    def _compute_is_l10n_ro_nondeductible(self):
        for record in self:
            if record.is_l10n_ro_record:
                record.l10n_ro_is_nondeductible = any(
                    record.invoice_repartition_line_ids.mapped("l10n_ro_nondeductible")
                    + record.refund_repartition_line_ids.mapped("l10n_ro_nondeductible")
                )
            else:
                record.l10n_ro_is_nondeductible = False

    @api.model
    def _prepare_tax_lines(self, base_lines, company, tax_lines=None):
        print("base_lines to process: ", base_lines)
        print("tax_lines to process: ", tax_lines)
        res = super()._prepare_tax_lines(base_lines, company, tax_lines=tax_lines)
        base_lines_to_update = res.get("base_lines_to_update", [])
        # print(res)
        for (base_line, vals) in base_lines_to_update:
            if (
                isinstance(base_line["record"], models.Model)
                and base_line["record"]._name == "account.move.line"
            ):
                aml = base_line["record"]
                if aml.display_type == "non_deductible_product":
                    # Remove the tax
                    vals["tax_ids"] = [Command.set([])]
                    tags = aml.l10n_ro_non_deductible_line_id.tax_tag_ids
                    if tags:
                        vals["tax_tag_ids"] = [Command.set(tags.ids)]
                if aml.display_type == "non_deductible_product_total":
                    tags = aml.l10n_ro_non_deductible_line_id.tax_tag_ids.l10n_ro_nondeductible_tag_id
                    if tags:
                        vals["tax_tag_ids"] = [Command.set(tags.ids)]
                    else:
                        vals["tax_tag_ids"] = [Command.set(aml.l10n_ro_non_deductible_line_id.tax_tag_ids.ids)]
                # if aml.display_type == "non_deductible_tax" and aml.name != _('private part'):
                #     tags = aml.tax_tag_ids.l10n_ro_nondeductible_tag_id
                #     if tags:
                #         vals["tax_tag_ids"] = [Command.set(tags.ids)]
                #     else:
                #         vals["tax_tag_ids"] = [Command.set(aml.tax_tag_ids.ids)]
        return res

