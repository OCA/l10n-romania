# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "l10n.ro.mixin"]

    l10n_ro_nondeductible_tax_id = fields.Many2one(
        "account.tax",
        string="Romania - Non Deductible Tax",
        domain=[("l10n_ro_is_nondeductible", "=", True)],
        copy=False,
    )
    l10n_ro_nondeductible_percent = fields.Selection(
        [("0", "Deductible"), ("50", "50% Nondeductible"), ("100", "Nondeductible")],
        string="Romania - Non Deductible Percent",
        default="0",
    )
    l10n_ro_nondeductible_usage = fields.Boolean(
        compute="_compute_l10n_ro_nondeductible_usage",
        string="Romania - Allow Non Deductible",
    )

    def _l10n_ro_checkUsageLocation(self, listUsageLocation):
        permit_location_usage = ["usage_giving", "consume", "inventory"]
        return any([u in permit_location_usage for u in listUsageLocation])

    @api.depends("location_dest_id", "location_id")
    def _compute_l10n_ro_nondeductible_usage(self):
        for s in self:
            if s.is_l10n_ro_record:
                s.l10n_ro_nondeductible_usage = self._l10n_ro_checkUsageLocation(
                    [s.location_dest_id.usage, s.location_id.usage]
                )
            else:
                s.l10n_ro_nondeductible_usage = False

    def _get_account_move_line_vals(self):
        # For nondeductible operation, add the taxes to the expense debit line
        res = super()._get_account_move_line_vals()
        if self.l10n_ro_nondeductible_tax_id:
            for line in res:
                account = self.env["account.account"].browse(line["account_id"])
                if account.account_type == "expense":
                    line.update(
                        {
                            "tax_ids": [(6, 0, [self.l10n_ro_nondeductible_tax_id.id])],
                            "deductible_amount": 100
                            - int(self.l10n_ro_nondeductible_percent),
                        }
                    )
        return res
