# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import _, api, models
from odoo.tools import frozendict


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    def l10n_ro_fix_nondeductible_vat_lines(self):
        moves = self.env["account.move"]
        to_remove_lines = self.env["account.move.line"]
        for line in self.filtered(lambda l: l.company_id.l10n_ro_accounting):
            move = line.move_id
            tax_rep_line = line.tax_repartition_line_id
            # Remove the lines marked to be removed from stock non deductible
            if (
                line.display_type == "tax"
                and move.stock_move_id.l10n_ro_nondeductible_tax_id
                and tax_rep_line.l10n_ro_exclude_from_stock
            ):
                moves |= line.move_id
                to_remove_lines |= line
        to_remove_lines.with_context(dynamic_unlink=True).sudo().unlink()
        moves._sync_dynamic_lines(container={"records": moves, "self": moves})
        return to_remove_lines

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        to_remove_lines = lines.l10n_ro_fix_nondeductible_vat_lines()
        return lines - to_remove_lines

    @api.depends(
        "tax_ids",
        "currency_id",
        "partner_id",
        "analytic_distribution",
        "balance",
        "partner_id",
        "move_id.partner_id",
        "price_unit",
        "quantity",
    )
    def _compute_all_tax(self):
        res = super()._compute_all_tax()
        non_ded_ro_lines = self.filtered(
            lambda l: l.company_id.l10n_ro_accounting
            and l.tax_ids.filtered(lambda t: t.l10n_ro_is_nondeductible)
        )
        for line in non_ded_ro_lines:
            sign = line.move_id.direction_sign
            if line.display_type == "product" and line.move_id.is_invoice(True):
                amount_currency = sign * line.price_unit * (1 - line.discount / 100)
                handle_price_include = True
                quantity = line.quantity
            else:
                amount_currency = line.amount_currency
                handle_price_include = False
                quantity = 1
            compute_all_currency = line.tax_ids.with_context(
                l10n_ro_account_id=line.account_id
            ).compute_all(
                amount_currency,
                currency=line.currency_id,
                quantity=quantity,
                product=line.product_id,
                partner=line.move_id.partner_id or line.partner_id,
                is_refund=line.is_refund,
                handle_price_include=handle_price_include,
                include_caba_tags=line.move_id.always_tax_exigible,
                fixed_multiplicator=sign,
            )
            rate = line.amount_currency / line.balance if line.balance else 1
            line.compute_all_tax_dirty = True
            line.compute_all_tax = {
                frozendict(
                    {
                        "tax_repartition_line_id": tax["tax_repartition_line_id"],
                        "group_tax_id": tax["group"] and tax["group"].id or False,
                        "account_id": tax["account_id"] or line.account_id.id,
                        "currency_id": line.currency_id.id,
                        "analytic_distribution": (
                            (tax["analytic"] or not tax["use_in_tax_closing"])
                            and line.move_id.state == "draft"
                        )
                        and line.analytic_distribution,
                        "tax_ids": [(6, 0, tax["tax_ids"])],
                        "tax_tag_ids": [(6, 0, tax["tag_ids"])],
                        "partner_id": line.move_id.partner_id.id or line.partner_id.id,
                        "move_id": line.move_id.id,
                        "display_type": line.display_type,
                    }
                ): {
                    "name": tax["name"]
                    + (" " + _("(Discount)") if line.display_type == "epd" else ""),
                    "balance": tax["amount"] / rate,
                    "amount_currency": tax["amount"],
                    "tax_base_amount": tax["base"]
                    / rate
                    * (-1 if line.tax_tag_invert else 1),
                }
                for tax in compute_all_currency["taxes"]
                if tax["amount"]
            }
            if not line.tax_repartition_line_id:
                line.compute_all_tax[frozendict({"id": line.id})] = {
                    "tax_tag_ids": [(6, 0, compute_all_currency["base_tags"])],
                }
        return res
