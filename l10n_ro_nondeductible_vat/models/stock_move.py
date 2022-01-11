# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    nondeductible_tax_id = fields.Many2one(
        "account.tax", domain=[("is_nondeductible", "=", True)], copy=False
    )
    nondeductible_usage = fields.Boolean(compute="_compute_nondeductible_usage")

    def _checkUsageLocation(self, listUsageLocation):
        permit_location_usage = ["usage_giving", "consume", "inventory"]
        return any([u in permit_location_usage for u in listUsageLocation])

    @api.depends("location_dest_id", "location_id")
    def _compute_nondeductible_usage(self):
        for s in self:
            s.nondeductible_usage = self._checkUsageLocation(
                [s.location_dest_id.usage, s.location_id.usage]
            )

    def _generate_valuation_lines_data(
        self,
        partner_id,
        qty,
        debit_value,
        credit_value,
        debit_account_id,
        credit_account_id,
        description,
    ):
        res = super(StockMove, self)._generate_valuation_lines_data(
            partner_id,
            qty,
            debit_value,
            credit_value,
            debit_account_id,
            credit_account_id,
            description,
        )
        if self.nondeductible_tax_id:
            if res.get("debit_line_vals"):
                res["debit_line_vals"].update(
                    {
                        "tax_ids": [(6, 0, [self.nondeductible_tax_id.id])],
                    }
                )
        return res
