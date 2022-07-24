# Copyright (C) 2022 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        if (
            len(self) == 1
            and self.move_type in ["in_invoice", "in_refund"]
            and self.company_id.romanian_accounting
            and not self.env.context.get("l10n_ro_approved_price_difference")
        ):
            action = self._get_price_difference_check_action()
            if action:
                return action
        self.fix_price_difference_svl()
        res = super().action_post()
        return res

    def _get_price_difference_check_action(self):
        self.ensure_one()
        price_diffs = []  # list of (product, picking)
        for invoice in self:
            if invoice.move_type in ["in_invoice", "in_refund"]:
                invoice_lines = invoice.invoice_line_ids.filtered(
                    lambda l: not l.display_type and l.purchase_line_id
                )
                for line in invoice_lines:
                    add_diff = False
                    if line.product_id.cost_method != "standard":
                        add_diff = invoice.company_id.stock_acc_price_diff

                    if add_diff:
                        # se reevalueaza stocul
                        price_diff, qty_diff = line.get_stock_valuation_difference()
                        if price_diff:
                            valuation_stock_moves = line._get_valuation_stock_moves()
                            price_diffs.append(
                                (
                                    valuation_stock_moves.mapped("product_id"),
                                    valuation_stock_moves.mapped("picking_id"),
                                    price_diff,
                                    qty_diff,
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

    def fix_price_difference_svl(self):
        for invoice in self:
            if invoice.move_type in ["in_invoice", "in_refund"]:
                invoice_lines = invoice.invoice_line_ids.filtered(
                    lambda l: not l.display_type and l.purchase_line_id
                )
                for line in invoice_lines:
                    add_diff = False
                    if line.product_id.cost_method != "standard":
                        add_diff = not invoice.company_id.stock_acc_price_diff

                    if not add_diff:
                        # se reevalueaza stocul
                        price_diff, _qty_diff = line.get_stock_valuation_difference()
                        if price_diff:
                            line.modify_stock_valuation(price_diff)

    def _stock_account_prepare_anglo_saxon_in_lines_vals(self):
        if self.company_id.romanian_accounting:
            return []
        return super()._stock_account_prepare_anglo_saxon_in_lines_vals()
