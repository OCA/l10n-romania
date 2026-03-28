# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    l10n_ro_cost_type = fields.Selection(
        selection_add=[("price_diff", "Price Difference")],
        ondelete={"price_diff": "set default"},
    )

    def _compute_l10n_ro_only_on_distributed_lines(self):
        res = super()._compute_l10n_ro_only_on_distributed_lines()
        ro_price_diff_lc = self.filtered(
            lambda lc: lc.l10n_ro_cost_type == "price_diff" and lc.is_l10n_ro_record
        )
        ro_price_diff_lc.l10n_ro_only_on_distributed_lines = True
        return res

    def _get_targeted_move_ids(self):
        if not self.env.context.get("l10n_ro_price_difference_move_ids"):
            return super()._get_targeted_move_ids()

        return self.env["stock.move"].browse(
            self.env.context["l10n_ro_price_difference_move_ids"]
        )

    def _create_account_move_line(
        self, credit_account_id, debit_account_id, remaining_qty
    ):
        l10n_ro_records = self.filtered("is_l10n_ro_record")
        if not l10n_ro_records and credit_account_id == debit_account_id:
            return self.env["account.move.line"]

        return super()._create_account_move_line(
            credit_account_id, debit_account_id, remaining_qty
        )
