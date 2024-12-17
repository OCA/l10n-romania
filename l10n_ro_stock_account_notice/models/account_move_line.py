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
        res = super()._compute_account_id()
        l10n_ro_lines = self.filtered(
            lambda x: x.product_id.type == "product" and x.is_l10n_ro_record
        )

        company = (
            self.env["res.company"].browse(self._context.get("force_company"))
            or self.env.company
        )

        stock_picking_payable_account_id = (
            company.l10n_ro_property_stock_picking_payable_account_id
        )
        stock_picking_receivable_account_id = (
            company.l10n_ro_property_stock_picking_receivable_account_id
        )

        for line in l10n_ro_lines:
            move_id = line.move_id
            if move_id.is_purchase_document() and stock_picking_payable_account_id:
                purchase = line.mapped("purchase_order_id")
                if not purchase:
                    continue

                is_notice = any([p.l10n_ro_notice for p in purchase.picking_ids])
                if is_notice:
                    line.account_id = stock_picking_payable_account_id

            if move_id.is_sale_document() and stock_picking_receivable_account_id:
                sale_lines = line.mapped("sale_line_ids")
                if not sale_lines:
                    continue
                is_notice = any(
                    [
                        p.l10n_ro_notice
                        for p in sale_lines.mapped("order_id").mapped("picking_ids")
                    ]
                )
                if is_notice:
                    line.account_id = stock_picking_receivable_account_id

        return res

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
