# Copyright (C) 2022 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, models
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
                    lambda l: not l.display_type and l.purchase_line_id
                )
                for line in invoice_lines:
                    add_diff = invoice.company_id.l10n_ro_stock_acc_price_diff
                    if line.product_id.cost_method == "standard":
                        add_diff = False
                    if add_diff:
                        # se reevalueaza stocul
                        (
                            price_diff,
                            qty_diff,
                        ) = line.l10n_ro_get_stock_valuation_difference()
                        if price_diff:
                            valuation_stock_moves = (
                                line._l10n_ro_get_valuation_stock_moves()
                            )
                            price_diffs.append(
                                (
                                    valuation_stock_moves.mapped("product_id"),
                                    valuation_stock_moves.mapped("picking_id"),
                                    line.currency_id.round(price_diff),
                                    float_round(
                                        qty_diff,
                                        precision_rounding=line.product_uom_id.rounding,
                                    ),
                                )
                            )

        if price_diffs:
            tbody = ""
            for pd in price_diffs:
                tbody += (
                    "<tr>"
                    f"<td>{pd[0].name_get()[0][1]}</td>"
                    f"<td>{', '.join(pd[1].mapped('name'))}</td>"
                    f"<td>{pd[2]}</td>"
                    f"<td>{pd[3]}</td>"
                    "</tr>"
                )

            message = """
            <table class="small table table-bordered text-center">
                <tr>
                    <th>Product</th>
                    <th>Pickings</th>
                    <th>Price Difference</th>
                    <th>Quantity Difference</th>
                </tr>
                {}
            </table>

            """.format(
                tbody
            )
            wizard = self.env["l10n_ro.price_difference_confirm_dialog"].create(
                {"invoice_id": self.id, "message": message}
            )

            view = self.env.ref(
                "l10n_ro_stock_price_difference.view_price_difference_confirmation_form"
            )
            return {
                "name": _("Confirm Price Difference ?"),
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "res_model": "l10n_ro.price_difference_confirm_dialog",
                "res_id": wizard.id,
                "views": [(view.id, "form")],
                "view_id": view.id,
                "target": "new",
                "context": dict(self.env.context),
            }
        return False

    def l10n_ro_fix_price_difference_svl(self):
        for invoice in self:
            if invoice.state == "posted" and invoice.move_type in [
                "in_invoice",
                "in_refund",
            ]:
                invoice_lines = invoice.invoice_line_ids.filtered(
                    lambda l: not l.display_type and l.purchase_line_id
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
                            line.l10n_ro_modify_stock_valuation(diff, line)

    def _stock_account_prepare_anglo_saxon_in_lines_vals(self):
        l10n_ro_moves = self.filtered(lambda m: m.company_id.l10n_ro_accounting)
        if l10n_ro_moves == self:
            return []
        return super(
            AccountMove, self - l10n_ro_moves
        )._stock_account_prepare_anglo_saxon_in_lines_vals()
