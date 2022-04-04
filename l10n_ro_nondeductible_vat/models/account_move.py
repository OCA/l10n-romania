# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _preprocess_taxes_map(self, taxes_map):
        """In case of stock not deductible, remove the line set to be excluded"""
        new_taxes_map = {}
        res = super()._preprocess_taxes_map(taxes_map)
        for key, vals in res.items():
            if not vals.get("grouping_dict"):
                new_taxes_map[key] = taxes_map[key]
            else:
                group = vals.get("grouping_dict")
                if not group.get("exlude_from_stock"):
                    new_taxes_map[key] = taxes_map[key]
        return new_taxes_map

    @api.model
    def _get_tax_grouping_key_from_base_line(self, base_line, tax_vals):
        """
        Update tax grouping account_id with the nondeductible one defined in account.
        """
        is_from_stock = base_line.move_id.stock_move_id
        tax_repartition_line = self.env["account.tax.repartition.line"].browse(
            tax_vals["tax_repartition_line_id"]
        )
        res = super()._get_tax_grouping_key_from_base_line(base_line, tax_vals)
        if is_from_stock and tax_repartition_line.exclude_from_stock:
            res["exlude_from_stock"] = tax_repartition_line.exclude_from_stock
        tax_repartition_line = self.env["account.tax.repartition.line"].browse(
            tax_vals["tax_repartition_line_id"]
        )
        if (
            base_line.account_id.nondeductible_account_id
            and tax_repartition_line.nondeductible
        ):
            res["account_id"] = base_line.account_id.nondeductible_account_id.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves_from_stock = moves.filtered("stock_move_id")
        for move in moves_from_stock:
            move_have_taxes = move.line_ids.filtered("tax_ids")
            if move_have_taxes:
                move.with_context(check_move_validity=False)._recompute_dynamic_lines(
                    True, True
                )
        return moves
