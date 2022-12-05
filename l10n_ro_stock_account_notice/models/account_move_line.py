# Copyright (C) 2022 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    def _get_computed_account(self):
        if self.product_id.type == "product" and self.is_l10n_ro_record:
            if self.move_id.is_purchase_document():
                purchase = self.purchase_order_id
                if purchase and self.product_id.purchase_method == "receive":
                    # Control bills based on received quantities
                    if any(
                        [
                            p.l10n_ro_notice or p._is_dropshipped()
                            for p in purchase.picking_ids
                        ]
                    ):
                        self = self.with_context(valued_type="invoice_in_notice")
                    else:
                        self = self.with_context(valued_type="invoice_in")
            if self.move_id.is_sale_document():
                sales = self.sale_line_ids
                if sales and self.product_id.invoice_policy == "delivery":
                    # Control bills based on received quantities
                    sale = self.sale_line_ids[0].order_id
                    if any(
                        [
                            p.l10n_ro_notice and not p._is_dropshipped()
                            for p in sale.picking_ids
                        ]
                    ):
                        self = self.with_context(valued_type="invoice_out_notice")
                    else:
                        self = self.with_context(valued_type="invoice_out")
        return super(AccountMoveLine, self)._get_computed_account()

    def _get_account_change_stock_moves_purchase(self):
        stock_moves = super()._get_account_change_stock_moves_purchase()
        return stock_moves.filtered(lambda sm: not sm.picking_id.l10n_ro_notice)

    def _get_account_change_stock_moves_sale(self):
        stock_moves = super()._get_account_change_stock_moves_sale()
        return stock_moves.filtered(lambda m: not m.picking_id.l10n_ro_notice)
