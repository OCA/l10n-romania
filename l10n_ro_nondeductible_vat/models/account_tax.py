# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountTaxExtend(models.Model):
    _inherit = "account.tax"

    nondeductible_tax_id = fields.Many2one("account.tax", copy=False)
    is_nondeductible = fields.Boolean(
        compute="_compute_boolean_nondeductible", store=True
    )

    @api.depends("invoice_repartition_line_ids", "refund_repartition_line_ids")
    def _compute_boolean_nondeductible(self):
        for record in self:
            record.is_nondeductible = any(
                record.invoice_repartition_line_ids.mapped("nondeductible")
                + record.refund_repartition_line_ids.mapped("nondeductible")
            )


class AccountTaxRepartitionLineExtend(models.Model):
    _inherit = "account.tax.repartition.line"

    nondeductible = fields.Boolean()
    exclude_from_stock = fields.Boolean()
