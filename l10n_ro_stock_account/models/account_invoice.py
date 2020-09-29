# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, models
from odoo.tools import safe_eval
from odoo.tools.float_utils import float_is_zero

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _stock_account_prepare_anglo_saxon_in_lines_vals(self):
        # inainte de a genera liniile de diferenta de pret
        for invoice in self:
            account_id = invoice.company_id.property_stock_picking_payable_account_id
            if invoice.type in ["in_invoice", "in_refund"]:
                for line in invoice.invoice_line_ids:
                    add_diff = False
                    if line.product_id.cost_method == "standard":
                        # daca pretul este standard se inregistreaza
                        # diferentele de pret.
                        add_diff = True
                    else:
                        add_diff = invoice.company_id.stock_acc_price_diff

                    # daca linia a fost receptionata pe baza de aviz se
                    # seteaza contul 408 pe nota contabile
                    if account_id and line.account_id == account_id:
                        # trebuie sa adaug diferenta dintre receptie pe
                        # baza de aviz si receptia din factura
                        add_diff = True
                    if add_diff:
                        # se reevalueaza stocul
                        price_diff = line.get_stock_valuation_difference()
                        print(line.name)
                        print("Price diff")
                        print(price_diff)
                        if price_diff:
                            line.modify_stock_valuation(price_diff)

        lines_vals_list = super(
            AccountMove, self
        )._stock_account_prepare_anglo_saxon_in_lines_vals()

        return lines_vals_list

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        # nu se mai face descarcarea de gestiune la facturare
        return []

    def post(self):
        res = super(AccountMove, self).post()
        for move in self:
            for line in move.line_ids:
                _logger.info(
                    "%s\t\t\t\t%s\t\t\t%s"
                    % (line.debit, line.credit, line.account_id.display_name)
                )
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_computed_account(self):
        if (
            self.product_id.type == "product"
            and self.move_id.company_id.anglo_saxon_accounting
        ):
            if self.move_id.is_purchase_document():
                purchase = self.move_id.purchase_id
                if purchase and self.product_id.purchase_method == "receive":
                    # Control bills based on received quantities
                    if any([p.notice for p in purchase.picking_ids]):
                        self = self.with_context(valued_type="invoice_in_notice")
            if self.move_id.is_sale_document():
                sales = self.sale_line_ids
                if sales and self.product_id.invoice_policy == "delivery":
                    # Control bills based on received quantities
                    sale = self.sale_line_ids[0].order_id
                    if any([p.notice for p in sale.picking_ids]):
                        self = self.with_context(valued_type="invoice_out_notice")
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
                stock_moves = self.purchase_line_id.move_ids.filtered(
                    lambda sm: not sm.picking_id.notice
                )
                for stock_move in stock_moves.filtered(lambda m: m.state == "done"):
                    if stock_move.location_dest_id.property_stock_valuation_account_id:
                        location = stock_move.location_dest_id
                        res = location.property_stock_valuation_account_id
            if self.move_id.is_sale_document():
                sales = self.sale_line_ids.filtered(lambda s: s.move_ids)
                for sale in sales:
                    for stock_move in sale.move_ids.filtered(
                        lambda m: not m.picking_id.notice and m.state == "done"
                    ):
                        location = stock_move.location_id
                        res = location.property_account_income_location_id
            if fiscal_position:
                res = fiscal_position.map_account(res)
        return res

    def get_stock_valuation_difference(self):
        """ Se obtine diferenta dintre evaloarea stocului si valoarea din factura"""
        line = self
        move = line.move_id
        # Retrieve stock valuation moves.
        valuation_stock_moves = self.env["stock.move"].search(
            [
                ("purchase_line_id", "=", line.purchase_line_id.id),
                ("state", "=", "done"),
                ("product_qty", "!=", 0.0),
            ]
        )
        if move.type == "in_refund":
            valuation_stock_moves = valuation_stock_moves.filtered(
                lambda stock_move: stock_move._is_out()
            )
        else:
            valuation_stock_moves = valuation_stock_moves.filtered(
                lambda stock_move: stock_move._is_in()
            )

        if not valuation_stock_moves:
            return 0.0

        valuation_price_unit_total = 0
        valuation_total_qty = 0
        for val_stock_move in valuation_stock_moves:
            svl = val_stock_move.mapped("stock_valuation_layer_ids").filtered(
                lambda l: l.quantity
            )
            layers_qty = sum(svl.mapped("quantity"))
            layers_values = sum(svl.mapped("value"))

            valuation_price_unit_total += layers_values
            valuation_total_qty += layers_qty

        precision = line.product_uom_id.rounding or line.product_id.uom_id.rounding
        if float_is_zero(valuation_total_qty, precision_rounding=precision):
            return 0.0

        valuation_price_unit = valuation_price_unit_total / valuation_total_qty
        price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
        if line.tax_ids:
            price_unit = line.tax_ids.compute_all(
                price_unit,
                currency=move.currency_id,
                quantity=1.0,
                is_refund=move.type == "in_refund",
            )["total_excluded"]

        price_unit = line.product_uom_id._compute_price(
            price_unit, line.product_id.uom_id
        )

        price_unit = move.currency_id._convert(
            price_unit,
            move.company_currency_id,
            move.company_id,
            move.invoice_date,
            round=False,
        )
        price_unit_val_dif = price_unit - valuation_price_unit
        return price_unit_val_dif

    def modify_stock_valuation(self, price_unit_val_dif):
        # se adauga la evaluarea miscarii de stoc
        valuation_stock_move = self.env["stock.move"].search(
            [
                ("purchase_line_id", "=", self.purchase_line_id.id),
                ("state", "=", "done"),
                ("product_qty", "!=", 0.0),
            ],
            limit=1,
        )
        print(valuation_stock_move.ids)
        linked_layer = valuation_stock_move.stock_valuation_layer_ids[:1]
        value = price_unit_val_dif * self.quantity
        print(linked_layer)
        print(value)
        # trebuie cantitate din factura in unitatea produsului si apoi
        value = self.product_uom_id._compute_price(value, self.product_id.uom_id)

        print(value)
        svl = self.env["stock.valuation.layer"].create(
            {
                "value": value,
                "unit_cost": 0,
                "quantity": 1e-50,
                # in _stock_account_prepare_anglo_saxon_in_lines_vals
                # se face filtrarea dupa cantitate
                "remaining_qty": 0,
                "stock_valuation_layer_id": linked_layer.id,
                "description": _("Price difference"),
                "stock_move_id": valuation_stock_move.id,
                "product_id": self.product_id.id,
                "company_id": self.move_id.company_id.id,
            }
        )
        print(svl.id)
