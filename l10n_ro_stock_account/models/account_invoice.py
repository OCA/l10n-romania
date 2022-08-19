# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        # nu se mai face descarcarea de gestiune la facturare
        invoices = self
        for move in self:
            if move.company_id.romanian_accounting:
                invoices -= move
        return super(
            AccountMove, invoices
        )._stock_account_prepare_anglo_saxon_out_lines_vals()

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for move in self:
            for line in move.line_ids:
                _logger.debug(
                    "%s\t\t%s\t\t%s"
                    % (line.debit, line.credit, line.account_id.display_name)
                )
            invoice_lines = move.invoice_line_ids.filtered(lambda l: not l.display_type)
            for line in invoice_lines:
                valuation_stock_moves = line._get_valuation_stock_moves()
                if valuation_stock_moves:
                    svls = valuation_stock_moves.sudo().mapped(
                        "stock_valuation_layer_ids"
                    )
                    svls = svls.filtered(lambda l: not l.invoice_line_id)
                    svls.write(
                        {"invoice_line_id": line.id, "invoice_id": line.move_id.id}
                    )

        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_valuation_stock_moves(self):
        valuation_stock_moves = False
        if self.purchase_line_id or self.sale_line_ids:
            domain = [
                ("state", "=", "done"),
                ("product_qty", "!=", 0.0),
            ]
            if self.purchase_line_id:
                domain += [("purchase_line_id", "=", self.purchase_line_id.id)]
            if self.sale_line_ids:
                domain += [("sale_line_id", "in", self.sale_line_ids.ids)]

            valuation_stock_moves = self.env["stock.move"].search(domain)

        return valuation_stock_moves

    def _get_computed_account(self):
        res = super(AccountMoveLine, self)._get_computed_account()
        # Take accounts from stock location in case the category allow changinc
        # accounts and the picking is not notice
        if (
            self.product_id.categ_id.stock_account_change
            and self.product_id.type == "product"
            and self.move_id.company_id.romanian_accounting
        ):
            fiscal_position = self.move_id.fiscal_position_id
            if self.move_id.is_purchase_document():
                stock_moves = self.purchase_line_id.move_ids
                for stock_move in stock_moves.filtered(lambda m: m.state == "done"):
                    if stock_move.location_dest_id.property_stock_valuation_account_id:
                        location = stock_move.location_dest_id
                        res = location.property_stock_valuation_account_id
            if self.move_id.is_sale_document():
                sales = self.sale_line_ids.filtered(lambda s: s.move_ids)
                for stock_move in sales.move_ids:
                    if stock_move.location_id.property_account_income_location_id:
                        location = stock_move.location_id
                        res = location.property_account_income_location_id
            if fiscal_position:
                res = fiscal_position.map_account(res)
        return res
