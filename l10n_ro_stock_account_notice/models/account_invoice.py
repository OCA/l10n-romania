# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# Copyright (C) 2022 Dakai Soft
# Copyright 2013-15 Agile Business Group sagl (<http://www.agilebg.com>)
# Copyright 2015-2016 AvanzOSC
# Copyright 2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2017 Jacques-Etienne Baudoux <je@bcim.be>
# Copyright 2020 Manuel Calero - Tecnativa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, api, models, fields
from odoo.tools.float_utils import float_is_zero

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"
    
    picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        string="Related Pickings",
        store=True,
        compute="_compute_picking_ids",
        help="Related pickings "
        "(only when the invoice has been generated from a sale order).",
    )
    
    # ==== Reverse feature fields ====
    notice_reversed_entry_id = fields.Many2one('account.move', string="Reversal of", readonly=True, copy=False,
        check_company=True)
    notice_reversal_move_id = fields.One2many('account.move', 'notice_reversed_entry_id')

    
    def _is_notice_inv(self):
        return any(self.mapped("picking_ids.notice"))

    @api.depends("invoice_line_ids", "invoice_line_ids.move_line_ids")
    def _compute_picking_ids(self):
        for invoice in self:
            invoice.picking_ids = invoice.mapped(
                "invoice_line_ids.move_line_ids.picking_id"
            )

    def action_show_picking(self):
        """This function returns an action that display existing pickings
        of given invoice.
        It can either be a in a list or in a form view, if there is only
        one picking to show.
        """
        self.ensure_one()
        form_view_name = "stock.view_picking_form"
        xmlid = "stock.action_picking_tree_all"
        action = self.env["ir.actions.act_window"]._for_xml_id(xmlid)
        if len(self.picking_ids) > 1:
            action["domain"] = "[('id', 'in', %s)]" % self.picking_ids.ids
        else:
            form_view = self.env.ref(form_view_name)
            action["views"] = [(form_view.id, "form")]
            action["res_id"] = self.picking_ids.id
        return action

    def _stock_account_prepare_ro_line_vals(self, account_id=None, lines_vals_list = [], call_sequence=0):

        # first call sequence
        if call_sequence == 0:
            if self._is_notice_inv() and account_id:
                rec_account = self.get_reception_account()
                if rec_account:
                    for line_vals in lines_vals_list:
                        if line_vals["account_id"] != account_id.id:
                            line_vals["account_id"] = rec_account.id

        # last call sequence
        elif call_sequence == 100:
            if not self._is_notice_inv():
                pass
        return lines_vals_list

    def is_reception_notice(self):
        self.ensure_one()
        return self._is_notice_inv()

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
    
    def _post(self, soft=True):
        to_post = super(AccountMove, self)._post(soft=soft)
        if self._context.get('link_move', None):
            self._context.get('link_move')._link_move(to_post)
        post_inv_notice_related = to_post.filtered(lambda x: x._is_notice_inv()).\
                                          mapped("notice_reversal_move_id").\
                                          filtered(lambda x: x.state !='posted')
        if post_inv_notice_related:
            post_inv_notice_related._post(soft=soft)
        return to_post
    
    def _add_diference_notice_invoice(self, lines): #[dict invoice lines]
        acc_move_lines = []
        acc_move_lines_vat = []
        move_line_entry_common = {
            'exclude_from_invoice_tab': True,
            }
        moveObj = self.env['stock.move']
        saleLineObj = self.env['sale.order.line']
        for _0, _0, line in lines:
            models._logger.error(line)
            if line.get('move_line_ids'):
                move_ids = moveObj.browse(line.get('move_line_ids')[0][-1])
                sale_order_line = saleLineObj.browse(line.get('sale_line_ids')[0][-1])
                company, currency = sale_order_line.order_id.company_id, sale_order_line.order_id.currency_id
                notice_move = move_ids._get_invoice_from_notice_account_move()
                models._logger.error("Notice Move %s" % notice_move)
                models._logger.error("Line Move %s" % line)
                models._logger.error("Line Calc %s" % [abs(notice_move.get('to_invoice')), currency._convert(
                    abs(line.get('price_unit') * line.get('quantity')), 
                    company.currency_id,
                    company,
                    fields.Date().today()
                    ), abs(notice_move.get('vat'))])
                diference = abs(notice_move.get('to_invoice')) - currency._convert(
                    abs(line.get('price_unit') * line.get('quantity')), 
                    company.currency_id,
                    company,
                    fields.Date().today()
                    ) - abs(notice_move.get('vat'))
                precision = company.currency_id.rounding
                if float_is_zero(diference, precision_rounding=precision):
                    diference = 0.0
                if diference != 0:
                    new_entry = move_line_entry_common.copy()
                    new_entry.update({
                        'name': line.get('name') + _(', price diference'),
                        'credit':diference < 0 and abs(diference) or 0,
                        'debit':diference > 0 and diference or 0,
                        'account_id': diference < 0 and company.income_currency_exchange_account_id.id or company.expense_currency_exchange_account_id.id,
                        'exclude_from_invoice_tab': False,
                        })
                    acc_move_lines.append(new_entry)
                if notice_move.get('vat', 0) != 0:
                    amount_vat = notice_move.get('vat', 0)
                    new_entry = move_line_entry_common.copy()
                    new_entry.update({
                        'name': line.get('name') + _(', VAT'),
                        'credit': amount_vat < 0 and abs(amount_vat) or 0,
                        'debit': amount_vat > 0 and amount_vat or 0,
                        'account_id': notice_move.get('vat_account_id').id,
                        })
                    acc_move_lines_vat.append(new_entry)
                    new_entry = move_line_entry_common.copy()
                    new_entry.update({
                        'name': line.get('name') + _(', VAT'),
                        'debit': amount_vat < 0 and abs(amount_vat) or 0,
                        'credit': amount_vat > 0 and amount_vat or 0,
                        'account_id': notice_move.get('account_id').id,
                        })
                    acc_move_lines_vat.append(new_entry)
        return acc_move_lines, acc_move_lines_vat
    
    def _link_reverse_account_move_notice(self, lines=[]):
        colect_moves = None
        move_orig = self.line_ids.mapped("move_line_ids.account_move_notice_id")
        if move_orig:
            colect_moves = move_orig
            move_orig.write({
                'notice_reversed_entry_id': self.id
                })
            # reverse VAT
            if lines:
                colect_moves |= move_orig[0].with_context({}).copy({
                    'line_ids': [(0, 0, move_line) for move_line in lines],
                    'name': "/".join(move_orig.mapped('name')),
                    'notice_reversed_entry_id': self.id
                    })
        return colect_moves
        
    
    #=============== ORM Methods
    
    @api.model
    def create(self, values):
        acc_move_lines = acc_move_lines_vat = []
        if self._context.get('picking_ids'):
            acc_move_lines, acc_move_lines_vat = self._add_diference_notice_invoice(values['invoice_line_ids'])
            if acc_move_lines:
                values['invoice_line_ids'] += [(0, 0, move_line) for move_line in acc_move_lines]
        res = super(AccountMove, self).create(values)
        res._link_reverse_account_move_notice(acc_move_lines_vat)
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    move_line_ids = fields.Many2many(
        comodel_name="stock.move",
        relation="stock_move_invoice_line_rel",
        column1="invoice_line_id",
        column2="move_id",
        string="Related Stock Moves",
        readonly=True,
        help="Related stock moves "
        "(only when the invoice has been generated from a sale order).",
    )
    
    def _get_computed_account_purchase_context(self):
        if self.move_id.is_purchase_document():
            purchase = self.purchase_order_id
            if purchase and self.product_id.purchase_method == "receive":
                # Control bills based on received quantities
                if any(
                    [p.notice or p._is_dropshipped() for p in purchase.picking_ids]
                ):
                    self = self.with_context(valued_type="invoice_in_notice")
        return self

    def _get_computed_account_sale_context(self):
        if self.move_id.is_sale_document():
            sales = self.sale_line_ids
            if sales and self.product_id.invoice_policy == "delivery":
                # Control bills based on received quantities
                sale = self.sale_line_ids[0].order_id
                if any(
                    [p.notice and not p._is_dropshipped() for p in sale.picking_ids]
                ):
                    self = self.with_context(valued_type="invoice_out_notice")
        return self


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
