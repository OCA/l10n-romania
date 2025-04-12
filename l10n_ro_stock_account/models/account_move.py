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
            if not (line.product_id.is_storable and line.move_id.is_l10n_ro_record):
                continue
            fiscal_position = line.move_id.fiscal_position_id
            accounts = line.product_id.product_tmpl_id.get_product_accounts(
                fiscal_pos=fiscal_position
            )
            account = False
            fiscal_positions = line.move_id.fiscal_position_id
            if line.move_id.is_purchase_document():
                account = accounts["stock_valuation"]
                pickings = line.purchase_line_id.order_id.picking_ids
                fiscal_positions |= pickings.mapped(
                    "picking_type_id.l10n_ro_fiscal_position_id"
                )
                stock_moves = line._get_account_change_stock_moves_purchase()
                for stock_move in stock_moves:
                    location = stock_move.location_dest_id
                    va = location.l10n_ro_property_stock_valuation_account_id
                    if va:
                        account = va
            if line.move_id.is_sale_document():
                pickings = line.sale_line_ids.mapped("order_id.picking_ids")
                fiscal_positions |= pickings.mapped(
                    "picking_type_id.l10n_ro_fiscal_position_id"
                )
                stock_moves = line._get_account_change_stock_moves_sale()
                for stock_move in stock_moves:
                    location = stock_move.location_id
                    ai = location.l10n_ro_property_account_income_location_id
                    if ai:
                        account = ai
            # fiscal_positions |= line.move_id.journal_id.l10n_ro_fiscal_position_id
            # for fiscal_position in fiscal_positions:
            #     account = fiscal_position.map_account(account or line.account_id)

            if account:
                line.account_id = account

        return res

    def _get_account_change_stock_moves_purchase(self):
        stock_moves = self.purchase_line_id.move_ids
        return stock_moves.filtered(lambda m: m.state == "done")

    def _get_account_change_stock_moves_sale(self):
        sales = self.sale_line_ids.filtered(lambda s: s.move_ids)
        return sales.move_ids

    def _prepare_create_values(self, vals_list):
        result_vals_list = super()._prepare_create_values(vals_list)
        for vals in result_vals_list:
            move_id = vals.get("move_id", False)
            account_id = vals.get("account_id", False)
            if move_id and account_id:
                move = self.env["account.move"].browse(move_id)
                account = self.env["account.account"].browse(account_id)
                journal = move.journal_id
                fiscal_position = journal.l10n_ro_fiscal_position_id
                if fiscal_position:
                    account = fiscal_position.map_account(account)
                    vals["account_id"] = account.id
        return result_vals_list
