# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    def button_create_landed_costs(self):
        """Update account of the landed cost ine with the one from invoice line."""

        res = super().button_create_landed_costs()
        landed_cost = self.env["stock.landed.cost"].browse(res.get("res_id"))
        if self.is_l10n_ro_record and landed_cost:
            picking_invoice_ids = (
                self.line_ids.mapped("purchase_line_id")
                .mapped("order_id")
                .mapped("picking_ids")
            )
            picking_landed_cost_ids = (
                self.env["stock.landed.cost"]
                .search([("state", "=", "done")])
                .mapped("picking_ids")
            )
            landed_cost.picking_ids = picking_invoice_ids.filtered(
                lambda l: l not in picking_landed_cost_ids and l.state == "done"
            )
            for line in landed_cost.cost_lines:
                invoice_line = self.line_ids.filtered(
                    lambda l: l.product_id == line.product_id
                )
                if invoice_line:
                    line.account_id = invoice_line[0].account_id
        return res

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        # nu se mai face descarcarea de gestiune la facturare
        invoices = self
        for move in self:
            if move.is_l10n_ro_record:
                invoices -= move
        return super(
            AccountMove, invoices
        )._stock_account_prepare_anglo_saxon_out_lines_vals()

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for move in self.filtered("is_l10n_ro_record"):
            for line in move.line_ids:
                _logger.debug(
                    "%s\t\t%s\t\t%s"
                    % (line.debit, line.credit, line.account_id.display_name)
                )
            invoice_lines = move.invoice_line_ids.filtered(lambda l: not l.display_type)
            for line in invoice_lines:
                valuation_stock_moves = line._l10n_ro_get_valuation_stock_moves()
                if valuation_stock_moves:
                    svls = valuation_stock_moves.sudo().mapped(
                        "stock_valuation_layer_ids"
                    )
                    svls = svls.filtered(lambda l: not l.l10n_ro_invoice_line_id)
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

    def _get_landed_costs_account(self, accounts):
        if (
            self.move_id.is_l10n_ro_record
            and self.product_type == "service"
            and self.is_landed_costs_line
            and self.move_id.move_type in ("out_invoice", "out_refund")
        ):
            return accounts["income"]

        return super()._get_landed_costs_account(accounts)

    @api.onchange("is_landed_costs_line")
    def _onchange_is_landed_costs_line(self):
        res = super()._onchange_is_landed_costs_line()
        if (
            self.move_id.is_l10n_ro_record
            and self.product_type == "service"
            and self.is_landed_costs_line
        ):
            accounts = self.product_id.product_tmpl_id._get_product_accounts()
            if self.move_id.move_type not in ("out_invoice", "out_refund"):
                self.account_id = accounts["expense"]
            else:
                self.account_id = accounts["income"]
        return res

    def _l10n_ro_get_valuation_stock_moves(self):
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
            self.product_id.categ_id.l10n_ro_stock_account_change
            and self.product_id.type == "product"
            and self.move_id.is_l10n_ro_record
        ):
            fiscal_position = self.move_id.fiscal_position_id
            if self.move_id.is_purchase_document():
                stock_moves = self._get_account_change_stock_moves_purchase()
                for stock_move in stock_moves:
                    if (
                        stock_move.location_dest_id.l10n_ro_property_stock_valuation_account_id
                    ):
                        location = stock_move.location_dest_id
                        res = location.l10n_ro_property_stock_valuation_account_id
            if self.move_id.is_sale_document():
                stock_moves = self._get_account_change_stock_moves_sale()
                for stock_move in stock_moves:
                    if (
                        stock_move.location_id.l10n_ro_property_account_income_location_id
                    ):
                        location = stock_move.location_id
                        res = location.l10n_ro_property_account_income_location_id
            if fiscal_position:
                res = fiscal_position.map_account(res)
        return res

    def _get_account_change_stock_moves_purchase(self):
        stock_moves = self.purchase_line_id.move_ids
        return stock_moves.filtered(lambda m: m.state == "done")

    def _get_account_change_stock_moves_sale(self):
        sales = self.sale_line_ids.filtered(lambda s: s.move_ids)
        return sales.move_ids
