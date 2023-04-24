# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import date

from odoo import api, models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    def _preprocess_taxes_map(self, taxes_map):
        """In case of stock not deductible, remove the line set to be excluded"""
        res = super()._preprocess_taxes_map(taxes_map)
        if not self.is_l10n_ro_record:
            return res

        new_taxes_map = {}

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
        if self.is_l10n_ro_record:
            if is_from_stock and tax_repartition_line.l10n_ro_exclude_from_stock:
                res[
                    "exlude_from_stock"
                ] = tax_repartition_line.l10n_ro_exclude_from_stock
            if (
                base_line.account_id.l10n_ro_nondeductible_account_id
                and tax_repartition_line.l10n_ro_nondeductible
            ):
                res[
                    "account_id"
                ] = base_line.account_id.l10n_ro_nondeductible_account_id.id

            if (
                base_line.account_id.l10n_ro_nondeductible_account_id.internal_group
                == "expense"
            ):
                for line in tax_repartition_line:
                    if line.l10n_ro_nondeductible or not line.account_id:
                        analytic_account_id = (
                            base_line.move_id.invoice_line_ids.filtered(
                                lambda l: l.account_id == base_line.account_id
                            )[0]
                        )
                        if analytic_account_id.analytic_account_id:
                            res[
                                "analytic_account_id"
                            ] = analytic_account_id.analytic_account_id.id
                        if analytic_account_id.analytic_tag_ids:
                            res["analytic_tag_ids"] = [
                                (6, 0, analytic_account_id.analytic_tag_ids.ids)
                            ]

        return res

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)

        ro_moves = moves.filtered("is_l10n_ro_record")
        if ro_moves:
            moves_from_stock = ro_moves.filtered("stock_move_id")
            for move in moves_from_stock:
                move_have_taxes = move.line_ids.filtered("tax_ids")
                if move_have_taxes:
                    move.with_context(
                        check_move_validity=False
                    )._recompute_dynamic_lines(True, True)
        return moves


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    @api.model
    def _get_default_tax_account(self, repartition_line):
        tax = repartition_line.tax_id
        if not tax.is_l10n_ro_record:
            return super()._get_default_tax_account(repartition_line)

        if (
            tax.tax_exigibility == "on_payment"
            and not repartition_line.l10n_ro_skip_cash_basis_account_switch
        ):
            account = tax.cash_basis_transition_account_id
        else:
            account = repartition_line.account_id
        return account

    @api.onchange("tax_ids")
    def onchange_l10n_ro_tax_ids(self):
        if self.is_l10n_ro_record:
            if not self.display_type and "in" in self.move_id.move_type:
                partner = (
                    self.env["res.partner"]._find_accounting_partner(self.partner_id)
                    or self.partner_id
                )
                ctx = dict(self._context)
                vatp = False

                if self.move_id.invoice_date:
                    ctx.update({"check_date": self.move_id.invoice_date})
                else:
                    ctx.update({"check_date": date.today()})

                if partner:
                    vatp = partner.with_context(**ctx)._check_vat_on_payment()

                if vatp:
                    taxes = self.tax_ids

                    if taxes and self.move_id.fiscal_position_id:
                        taxes = self.move_id.fiscal_position_id.map_tax(taxes)

                    self.tax_ids = taxes
