# Copyright (C) 2022 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models
from odoo.tools import float_round

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        l10n_ro_records = self.filtered("is_l10n_ro_record")
        if not l10n_ro_records:
            return super().action_post()

        if (
            len(self) == 1
            and self.move_type in ["in_invoice", "in_refund"]
            and self.company_id.l10n_ro_accounting
            and not self.env.context.get("l10n_ro_approved_price_difference")
        ):
            action = self._l10n_ro_get_price_difference_check_action()
            if action:
                return action
        res = super().action_post()
        l10n_ro_records.l10n_ro_fix_price_difference_svl()
        return res

    def _l10n_ro_get_price_difference_check_action(self):
        self.ensure_one()
        price_diffs = []  # list of (product, picking)
        for invoice in self:
            if invoice.move_type in ["in_invoice", "in_refund"]:
                invoice_lines = invoice.invoice_line_ids.filtered(
                    lambda l: l.display_type == "product" and l.purchase_line_id
                )
                for line in invoice_lines:
                    add_diff = invoice.company_id.l10n_ro_stock_acc_price_diff
                    if line.product_id.cost_method == "standard":
                        add_diff = False
                    if not add_diff:
                        continue

                    # se reevalueaza stocul
                    price_diff, qty_diff = line.l10n_ro_get_stock_valuation_difference()
                    if not price_diff:
                        continue

                    valuation_stock_moves = line._l10n_ro_get_valuation_stock_moves()
                    #  de regula e o singura inregistrare
                    move_count = len(valuation_stock_moves)
                    for stock_move in valuation_stock_moves:
                        price_diffs.append(
                            {
                                "invoice_id": self.id,
                                "product_id": stock_move.product_id.id,
                                "picking_id": stock_move.picking_id.id,
                                "amount_difference": line.currency_id.round(
                                    price_diff / move_count
                                ),
                                "quantity_difference": float_round(
                                    qty_diff / move_count,
                                    precision_rounding=line.product_uom_id.rounding,
                                ),
                            }
                        )

        if price_diffs:
            difference_confirm_dialog_value = {
                "invoice_id": self.id,
                "item_ids": [],
            }
            for pd in price_diffs:
                difference_confirm_dialog_value["item_ids"].append([0, 0, pd])

            wizard = self.env["l10n_ro.price_difference_confirm_dialog"].create(
                difference_confirm_dialog_value
            )

            action = self.env["ir.actions.actions"]._for_xml_id(
                "l10n_ro_stock_price_difference.action_price_difference_confirmation"
            )
            action["res_id"] = wizard.id

            return action
        return False

    def l10n_ro_fix_price_difference_svl(self):
        for invoice in self:
            if invoice.state == "posted" and invoice.move_type in [
                "in_invoice",
                "in_refund",
            ]:
                invoice_lines = invoice.invoice_line_ids.filtered(
                    lambda l: l.display_type == "product" and l.purchase_line_id
                )
                for line in invoice_lines:
                    add_diff = invoice.company_id.l10n_ro_stock_acc_price_diff
                    if line.product_id.cost_method == "standard":
                        add_diff = False

                    if add_diff:
                        # se reevalueaza stocul
                        (
                            diff,
                            _qty_diff,
                        ) = line.l10n_ro_get_stock_valuation_difference()
                        if diff:
                            line.l10n_ro_modify_stock_valuation(diff)

    def _stock_account_prepare_anglo_saxon_in_lines_vals(self):
        l10n_ro_moves = self.filtered(lambda m: m.company_id.l10n_ro_accounting)
        if l10n_ro_moves == self:
            return []
        return super(
            AccountMove, self - l10n_ro_moves
        )._stock_account_prepare_anglo_saxon_in_lines_vals()
