# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, models
from odoo.tools.float_utils import float_is_zero

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _stock_account_prepare_ro_line_vals(self, account_id=None, lines_vals_list = [], call_sequence=0):
        #TODO: Nu sunt tare multumit cu abordarea asta call_sequence,
        # De motificat intr-o forma mai viabila.
        return lines_vals_list


    def _stock_account_prepare_anglo_saxon_in_lines_vals(self):
        # inainte de a genera liniile de diferenta de pret

        lines_vals_list = []
        for invoice in self:
            account_id = invoice.company_id.property_stock_picking_payable_account_id
            if invoice.move_type in ["in_invoice", "in_refund"]:
                # Add new account moves for difference between reception
                # with notice and invoice values.
                lines_vals_list = super(
                        AccountMove, self
                    )._stock_account_prepare_anglo_saxon_in_lines_vals()


                lines_vals_list = invoice._stock_account_prepare_ro_line_vals(account_id=account_id, lines_vals_list = lines_vals_list, call_sequence=0)

                invoice_lines = invoice.invoice_line_ids.filtered(
                    lambda l: not l.display_type
                )
                for line in invoice_lines:
                    add_diff = False
                    if line.product_id.cost_method != "standard":
                        add_diff = not invoice.company_id.stock_acc_price_diff

                    # daca linia a fost receptionata pe baza de aviz se
                    # seteaza contul 408 pe nota contabile
                    # if account_id and line.account_id == account_id:
                    #     # trebuie sa adaug diferenta dintre receptie pe
                    #     # baza de aviz si receptia din factura
                    #     add_diff = True
                    # *** particularizarile au fost mutate pe un nou modul. ***

                    if not add_diff:
                        # se reevalueaza stocul
                        price_diff = line.get_stock_valuation_difference()
                        if price_diff:
                            line.sudo().modify_stock_valuation(price_diff)
                lines_vals_list = invoice._stock_account_prepare_ro_line_vals(
                    account_id=account_id, 
                    lines_vals_list = lines_vals_list or super(AccountMove, self)._stock_account_prepare_anglo_saxon_in_lines_vals(), 
                    call_sequence=100)
        return lines_vals_list

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

    def fix_price_difference_svl(self):
        for invoice in self:
            if invoice.move_type in ["in_invoice", "in_refund"]:
                invoice_lines = invoice.invoice_line_ids.filtered(
                    lambda l: not l.display_type
                )
                for line in invoice_lines:
                    add_diff = False
                    if line.product_id.cost_method != "standard":
                        add_diff = not invoice.company_id.stock_acc_price_diff

                    if not add_diff:
                        # se reevalueaza stocul
                        price_diff = line.get_stock_valuation_difference()
                        if price_diff:
                            line.modify_stock_valuation(price_diff)


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
            if self.move_id.move_type in ("in_refund", "out_invoice"):
                valuation_stock_moves = valuation_stock_moves.filtered(
                    lambda sm: sm._is_out()
                )
            else:
                valuation_stock_moves = valuation_stock_moves.filtered(
                    lambda sm: sm._is_in()
                )

        return valuation_stock_moves

    def _get_computed_account(self):
        if (
            self.product_id.type == "product"
            and self.move_id.company_id.anglo_saxon_accounting
        ):
            self = self.\
                _get_computed_account_purchase_context().\
                _get_computed_account_sale_context()
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
                stock_moves = self.purchase_line_id.move_ids._filter_move_for_account_move_line()
                for stock_move in stock_moves.filtered(lambda m: m.state == "done"):
                    if stock_move.location_dest_id.property_stock_valuation_account_id:
                        location = stock_move.location_dest_id
                        res = location.property_stock_valuation_account_id
            if self.move_id.is_sale_document():
                sales = self.sale_line_ids.filtered(lambda s: s.move_ids)
                for stock_move in sales.move_ids._filter_move_for_account_move_line():
                    if stock_move.location_id.property_account_income_location_id:
                        location = stock_move.location_id
                        res = location.property_account_income_location_id
            if fiscal_position:
                res = fiscal_position.map_account(res)
        return res


    def get_stock_valuation_difference(self):
        """Se obtine diferenta dintre evaloarea stocului si valoarea din factura"""
        line = self

        # Retrieve stock valuation moves.
        if not line.purchase_line_id:
            return 0.0

        valuation_stock_moves = self._get_valuation_stock_moves()

        if not valuation_stock_moves:
            return 0.0

        valuation_total = 0
        valuation_total_qty = 0
        for val_stock_move in valuation_stock_moves:
            svl = (
                val_stock_move.sudo()
                .mapped("stock_valuation_layer_ids")
                .filtered(lambda l: l.quantity)
            )
            layers_qty = sum(svl.mapped("quantity"))
            layers_values = sum(svl.mapped("value"))

            valuation_total += layers_values
            valuation_total_qty += layers_qty

        precision = line.product_uom_id.rounding or line.product_id.uom_id.rounding
        if float_is_zero(valuation_total_qty, precision_rounding=precision):
            return 0.0
        return abs(line.balance) - valuation_total

    def modify_stock_valuation(self, price_val_dif):
        # se adauga la evaluarea miscarii de stoc
        if not self.purchase_line_id:
            return 0.0
        valuation_stock_move = self.env["stock.move"].search(
            [
                ("purchase_line_id", "=", self.purchase_line_id.id),
                ("state", "=", "done"),
                ("product_qty", "!=", 0.0),
            ],
            limit=1,
        )
        linked_layer = valuation_stock_move.stock_valuation_layer_ids[:1]
        value = price_val_dif
        # trebuie cantitate din factura in unitatea produsului si apoi
        value = self.product_uom_id._compute_price(value, self.product_id.uom_id)

        self.env["stock.valuation.layer"].create(
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
                "invoice_line_id": self.id,
                "invoice_id": self.move_id.id,
            }
        )
        linked_layer.remaining_value += value
