# Copyright (C) 2022 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    def _compute_account_id(self):
        l10n_ro_lines_for_notice = self.filtered(
            lambda x: x.product_id.type == "product" and x.is_l10n_ro_record
        )
        valued_type = self.env.context.get("valued_type", self.move_id.move_type)
        remaining = self.with_context(valued_type=valued_type)
        invoice_in_notice_lines = self.env["account.move.line"].with_context(
            valued_type="invoice_in_notice"
        )
        invoice_out_notice_lines = self.env["account.move.line"].with_context(
            valued_type="invoice_out_notice"
        )

        for line in l10n_ro_lines_for_notice:
            move_id = line.move_id
            if move_id.is_purchase_document():
                purchase = line.mapped("purchase_order_id")
                if purchase and any(
                    [p.purchase_method == "receive" for p in line.mapped("product_id")]
                ):
                    # Control bills based on received quantities
                    if any(
                        [
                            p.l10n_ro_notice or p._is_dropshipped()
                            for p in purchase.picking_ids
                        ]
                    ):
                        invoice_in_notice_lines |= line
                        remaining -= line
            if move_id.is_sale_document():
                sale_lines = line.mapped("sale_line_ids")
                if sale_lines and any(
                    [p.invoice_policy == "delivery" for p in line.mapped("product_id")]
                ):
                    # Control bills based on received quantities
                    sale = sale_lines.mapped("order_id")
                    if any(
                        [
                            p.l10n_ro_notice and not p._is_dropshipped()
                            for p in sale.mapped("picking_ids")
                        ]
                    ):
                        invoice_out_notice_lines |= line
                        remaining -= line

        if invoice_in_notice_lines:
            super(AccountMoveLine, invoice_in_notice_lines)._compute_account_id()
        if invoice_out_notice_lines:
            super(AccountMoveLine, invoice_out_notice_lines)._compute_account_id()
        return super(AccountMoveLine, remaining)._compute_account_id()

    def _get_account_change_stock_moves_purchase(self):
        stock_moves = self.purchase_line_id.move_ids.filtered(
            lambda sm: not sm.picking_id.l10n_ro_notice
        )
        return stock_moves.filtered(lambda m: m.state == "done")

    def _get_account_change_stock_moves_sale(self):
        sales = self.sale_line_ids.filtered(lambda s: s.move_ids)
        return sales.move_ids.filtered(
            lambda m: not m.picking_id.l10n_ro_notice and m.state == "done"
        )
