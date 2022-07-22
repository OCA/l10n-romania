# Copyright (C) 2022 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def is_reception_notice(self):
        self.ensure_one()
        purchases = self.line_ids.mapped("purchase_line_id.order_id")
        picking_notice = self.env["stock.picking"].search(
            [
                ("id", "in", purchases.mapped("picking_ids").ids),
                ("state", "=", "done"),
                ("notice", "=", True),
            ]
        )
        if picking_notice:
            return True
        return False

    def get_reception_account(self):
        self.ensure_one()
        account = self.env["account.account"]
        acc_payable = self.company_id.property_stock_picking_payable_account_id
        valuation_stock_moves = self.env["stock.move"].search(
            [
                (
                    "purchase_line_id",
                    "in",
                    self.line_ids.mapped("purchase_line_id").ids,
                ),
                ("state", "=", "done"),
                ("picking_id.notice", "=", True),
                ("product_qty", "!=", 0.0),
            ]
        )
        if valuation_stock_moves:
            acc_moves = valuation_stock_moves.mapped("account_move_ids")
            lines = self.env["account.move.line"].search(
                [("move_id", "in", acc_moves.ids)]
            )
            lines_diff_acc = lines.mapped("account_id").filtered(
                lambda a: a != acc_payable
            )
            if lines_diff_acc:
                account = lines_diff_acc[0]
        return account

    def _stock_account_prepare_anglo_saxon_in_lines_vals(self):
        if self.company_id.romanian_accounting:
            return []
        return super()._stock_account_prepare_anglo_saxon_in_lines_vals()
