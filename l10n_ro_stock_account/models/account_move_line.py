# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    def _compute_account_id(self):
        # For Romania, we need to set the account based on the stock
        # move accounts, if the product is storable and if the move is
        # linked to a stock move.
        res = super()._compute_account_id()
        ro_lines = self.filtered(
            lambda line: line.product_id.is_storable and line.move_id.is_l10n_ro_record
        )
        for line in ro_lines:
            stock_move = line._get_stock_moves().filtered(lambda m: m.state == "done")
            if len(stock_move) > 1:
                stock_move = stock_move[-1]
            account = line.account_id
            if stock_move:
                move_type = stock_move.l10n_ro_move_type
                if not move_type:
                    move_type = stock_move._get_l10n_ro_move_type()
                product = line.product_id.with_context(l10n_ro_stock_move=stock_move)
                accounts = product.product_tmpl_id.get_product_accounts()
                ro_account = line._get_l10n_ro_line_account(
                    stock_move, line.product_id, accounts
                )
                if ro_account and ro_account != account:
                    account = ro_account
                    line.account_id = account
        return res

    def _get_l10n_ro_line_account(self, stock_move, product, accounts):
        self.ensure_one()
        if self.move_id.is_purchase_document():
            if product.is_storable:
                account = accounts["stock_valuation"]
                if stock_move.l10n_ro_move_type in (
                    "reception_notice",
                    "reception_notice_return",
                ):
                    if accounts.get("l10n_ro_picking_payable"):
                        account = accounts["l10n_ro_picking_payable"]
                if stock_move.l10n_ro_move_type in (
                    "reception_in_progress",
                    "reception_in_progress_return",
                ):
                    if accounts.get("l10n_ro_reception_in_progress"):
                        account = accounts["l10n_ro_reception_in_progress"]
            else:
                account = accounts["expense"]
        elif self.move_id.is_sale_document():
            account = accounts["income"]
            if stock_move.l10n_ro_move_type in (
                "delivery_notice",
                "delivery_notice_return",
            ):
                if accounts.get("l10n_ro_picking_receivable"):
                    account = accounts["l10n_ro_picking_receivable"]
        return account
