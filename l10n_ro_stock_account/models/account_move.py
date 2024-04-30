# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        # nu se mai face descarcarea de gestiune la facturare
        invoices = self
        for move in self:
            if move.company_id._check_is_l10n_ro_record():
                invoices -= move
        return super(
            AccountMove, invoices
        )._stock_account_prepare_anglo_saxon_out_lines_vals()

    def action_post(self):
        res = super().action_post()
        for move in self.filtered("is_l10n_ro_record"):
            for line in move.line_ids:
                _logger.debug(
                    f"{line.debit}\t\t{line.credit}\t\t{line.account_id.display_name}"
                )
            invoice_lines = move.invoice_line_ids.filtered(
                lambda line: line.display_type == "product"
            )
            for line in invoice_lines:
                valuation_stock_moves = line._l10n_ro_get_valuation_stock_moves()
                if valuation_stock_moves:
                    svls = valuation_stock_moves.sudo().mapped(
                        "stock_valuation_layer_ids"
                    )
                    svls = svls.filtered(
                        lambda layer: not layer.l10n_ro_invoice_line_id
                    )
                    svls.write(
                        {
                            "l10n_ro_invoice_line_id": line.id,
                            "l10n_ro_invoice_id": line.move_id.id,
                        }
                    )
        return res


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    def _l10n_ro_get_valuation_stock_moves(self):
        valuation_stock_moves = self.env["stock.move"]
        if self.purchase_line_id or self.sale_line_ids:
            domain = [("state", "=", "done"), ("product_qty", "!=", 0.0)]
            if self.purchase_line_id:
                domain += [("purchase_line_id", "=", self.purchase_line_id.id)]
            if self.sale_line_ids:
                domain += [("sale_line_id", "in", self.sale_line_ids.ids)]

            valuation_stock_moves = self.env["stock.move"].search(domain)

        return valuation_stock_moves

    def _compute_account_id(self):
        res = super()._compute_account_id()
        for line in self:
            if not (
                line.product_id.categ_id.l10n_ro_stock_account_change
                and line.product_id.type == "product"
                and line.move_id.is_l10n_ro_record
            ):
                continue
            account = False
            fiscal_position = line.move_id.fiscal_position_id
            if line.move_id.is_purchase_document():
                stock_moves = line._get_account_change_stock_moves_purchase()
                for stock_move in stock_moves:
                    location = stock_move.location_dest_id
                    va = location.l10n_ro_property_stock_valuation_account_id
                    if va:
                        account = va
            if line.move_id.is_sale_document():
                stock_moves = line._get_account_change_stock_moves_sale()
                for stock_move in stock_moves:
                    location = stock_move.location_id
                    ai = location.l10n_ro_property_account_income_location_id
                    if ai:
                        account = ai
            if fiscal_position:
                account = fiscal_position.map_account(account)

            if account:
                line.account_id = account
        return res

    def _get_account_change_stock_moves_purchase(self):
        stock_moves = self.purchase_line_id.move_ids
        return stock_moves.filtered(lambda m: m.state == "done")

    def _get_account_change_stock_moves_sale(self):
        sales = self.sale_line_ids.filtered(lambda s: s.move_ids)
        return sales.move_ids
