# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# Copyright (C) 2022 Dakai SOFT
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, models, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"
    
    invoice_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        relation="stock_move_invoice_line_rel",
        column1="move_id",
        column2="invoice_line_id",
        string="Invoice Line",
        copy=False,
        readonly=True,
    )
    account_move_notice_id = fields.Many2one('account.move')

    def _link_move(self, account_move_id):
        #require 1 move
        account_move_id.ensure_one()
        self.account_move_notice_id = account_move_id.id

    def _filter_move_for_account_move_line(self):
        return super(StockMove, self).filtered(
                    lambda sm: not sm.picking_id.notice
                )

    @api.model
    def _get_valued_types(self):
        valued_types = super(StockMove, self)._get_valued_types()
        valued_types += [
            "reception_notice",  # receptie de la furnizor cu aviz
            "reception_notice_return",  # retur receptie de la furnizor cu aviz
            "delivery_notice",
            "delivery_notice_return",
        ]
        return valued_types

    # evaluare la receptie - in mod normal nu se
    def _is_reception(self):
        """Este receptie in stoc fara aviz"""
        it_is = super(StockMove, self)._is_reception() and not self.picking_id.notice
        return it_is

    def _is_reception_return(self):
        """Este un retur la o receptie in stoc fara aviz"""
        it_is = super(StockMove, self)._is_reception_return() and not self.picking_id.notice
        return it_is

    def _is_reception_notice(self):
        """Este receptie in stoc cu aviz"""
        it_is = (
            self.company_id.romanian_accounting
            and self.picking_id.notice
            and self.location_id.usage == "supplier"
            and self._is_in()
        )
        return it_is

    def _create_reception_notice_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="reception_notice")
        return move._create_in_svl(forced_quantity)

    def _is_reception_notice_return(self):
        """Este un retur la receptie in stoc cu aviz"""
        it_is = (
            self.company_id.romanian_accounting
            and self.picking_id.notice
            and self.location_dest_id.usage == "supplier"
            and self._is_out()
        )
        return it_is

    def _create_reception_notice_return_svl(self, forced_quantity=None):
        svl = self.env["stock.valuation.layer"]
        for move in self:
            move = move.with_context(
                standard=True, valued_type="reception_notice_return"
            )
            if (
                move.origin_returned_move_id
                and move.origin_returned_move_id.sudo().stock_valuation_layer_ids
            ):
                move = move.with_context(
                    origin_return_candidates=move.origin_returned_move_id.sudo()
                    .stock_valuation_layer_ids.filtered(lambda sv: sv.remaining_qty > 0)
                    .ids
                )
            svl += move._create_out_svl(forced_quantity)
        return svl

    def _is_delivery(self):
        """Este livrare din stoc fara aviz"""
        return super(StockMove, self)._is_delivery() and not self.picking_id.notice

    def _is_delivery_return(self):
        """Este retur la o livrare din stoc fara aviz"""
        it_is = super(StockMove, self)._is_delivery_return() and not self.picking_id.notice
        return it_is

    def _is_delivery_notice(self):
        """Este livrare cu aviz"""
        it_is = (
            self.company_id.romanian_accounting
            and self.picking_id.notice
            and self.location_dest_id.usage == "customer"
            and self._is_out()
        )
        return it_is

    def _create_delivery_notice_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="delivery_notice")
        return move._create_out_svl(forced_quantity)

    def _is_delivery_notice_return(self):
        """Este retur livrare cu aviz"""
        it_is = (
            self.company_id.romanian_accounting
            and self.picking_id.notice
            and self.location_id.usage == "customer"
            and self._is_in()
        )
        return it_is

    def _create_delivery_notice_return_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="delivery_notice_return")
        return move._create_in_svl(forced_quantity)
    
    def _get_accounts_and_taxes(self, debit_account_id, credit_account_id):
        fpos = None
        tax_ids = None
        if (self._is_delivery_notice() or self._is_reception_notice_return()) and self.location_id.property_notice_position_id:
            fpos = self.location_id.property_notice_position_id
        elif (self._is_delivery_notice_return() or self._is_reception_notice()) and self.location_dest_id.property_notice_position_id:
            fpos = self.location_dest_id.property_notice_position_id
            
        if fpos:
            acc_obj = self.env['account.account']
            debit_account_id = fpos.map_account(acc_obj.browse(debit_account_id)).id
            credit_account_id = fpos.map_account(acc_obj.browse(credit_account_id)).id
            tax_ids = fpos.map_tax(self.sale_line_id.tax_id or self.purchase_line_id.taxes_id)
        
        return debit_account_id, credit_account_id, tax_ids

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, description):
        rslt = super(StockMove, self)._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, description)
        if self._context.get('valued_type', None) in [
            'invoice_out_notice', 'invoice_in_notice',
            'reception_notice',
            'reception_return_notice',
            ]:
            key_1 = 'credit_line_vals'
            key_2 = 'debit_line_vals'
            move_type = 0
            if self._context.get('valued_type', None) in ['invoice_out_notice', 'reception_return_notice']:
                move_type = -1
            if self._context.get('valued_type', None) in ['invoice_in_notice','reception_notice']:
                key_2, key_1 = key_1, key_2
                move_type = 1
                
            for key, _value in rslt.items():
                rslt[key].update({
                    'account_correspondence_id': rslt[key_1].get('account_id'),
                    })
                
            debit_account_id, credit_account_id, tax_ids = self._get_accounts_and_taxes(debit_account_id, credit_account_id)
            if self.company_id.property_notice_include_vat and tax_ids:
                tax_compute = tax_ids.compute_all(credit_value)
                rslt[key_1].update({
                    'move_line_ids': move_type < 0 and [(6, 0, self.move_line_ids.ids)] or [],
                    'credit': move_type < 0 and tax_compute.get('total_excluded') or 0,
                    'debit': move_type > 0 and tax_compute.get('total_included') or 0,
                    'exclude_from_invoice_tab': move_type > 0,
                    })
                rslt[key_2].update({
                    'move_line_ids': move_type > 0 and [(6, 0, self.move_line_ids.ids)] or [],
                    'debit': move_type < 0 and tax_compute.get('total_included') or 0,
                    'credit': move_type > 0 and tax_compute.get('total_excluded') or 0,
                    'exclude_from_invoice_tab': move_type < 0,
                    })
                models._logger.error([tax_compute, tax_ids])
                if tax_compute.get('total_included', 0) != tax_compute.get('total_excluded', 0):
                    for tax_dict in tax_compute.get('taxes', []):
                        rslt['vat_amount_%s' % tax_dict.get('id')] = {
                                'name': tax_dict.get('name'),
                                'product_id': self.product_id.id,
                                #'quantity': qty,
                                'ref': description,
                                'partner_id': partner_id,
                                'credit': move_type < 0 and tax_dict.get('amount', 0) or 0,
                                'debit': move_type > 0 and tax_dict.get('amount', 0) or 0,
                                'account_id': tax_dict.get('account_id'),
                                'account_correspondence_id': rslt['debit_line_vals'].get('account_id'),
                                'exclude_from_invoice_tab': True,
                            }
        models._logger.error(rslt)
        return rslt

    def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        self.ensure_one()
        AccountMove = self.env['account.move'].with_context(default_journal_id=journal_id)
    
        move_lines = self._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id, description)
        if move_lines:
            date = self._context.get('force_period_date', fields.Date.context_today(self))
            new_account_move = AccountMove.sudo().create({
                'journal_id': journal_id,
                'line_ids': move_lines,
                'date': date,
                'ref': description,
                'stock_move_id': self.id,
                'stock_valuation_layer_ids': [(6, None, [svl_id])],
                'move_type': 'entry',
            })
            new_account_move._post()

    def _romanian_account_entry_move(self, qty, description, svl_id, cost):
        super(StockMove, self)._romanian_account_entry_move(qty, description, svl_id, cost)
        svl = self.env["stock.valuation.layer"]
        if self._is_delivery_notice():
            # inregistrare valoare vanzare
            sale_amount = self._get_trade_amount()
            move = self.with_context(valued_type="invoice_out_notice", link_move=self)

            (
                journal_id,
                acc_src,
                acc_dest,
                acc_valuation,
            ) = move._get_accounting_data_for_valuation()
            move._create_account_move_line(
                acc_valuation, acc_dest, journal_id, qty, description, svl, sale_amount
            )

        if self._is_delivery_notice_return():
            # inregistrare valoare vanzare
            sale_amount = -1 * self._get_trade_amount()
            move = self.with_context(valued_type="invoice_out_notice", link_move=self)

            (
                journal_id,
                acc_src,
                acc_dest,
                acc_valuation,
            ) = move._get_accounting_data_for_valuation()
            move._create_account_move_line(
                acc_dest, acc_valuation, journal_id, qty, description, svl_id, sale_amount
            )


    def _get_trade_amount(self):
        valuation_amount = 0
        sale_line = self.sale_line_id
        purchase_line = self.purchase_line_id
        if sale_line and sale_line.product_uom_qty:
            price_invoice = self.price_unit
            if not price_invoice or price_invoice==0:
                price_invoice = sale_line.price_subtotal / sale_line.product_uom_qty
            price_invoice = sale_line.product_uom._compute_price(
                price_invoice, self.product_uom
            )
            valuation_amount = price_invoice * abs(self.product_qty)
            company = self.location_id.company_id or self.env.company
            valuation_amount = sale_line.order_id.currency_id._convert(
                valuation_amount, company.currency_id, company, self.date
            )
        elif purchase_line and purchase_line.product_uom_qty:
            price_invoice = self.price_unit
            if not price_invoice or price_invoice==0:
                price_invoice = purchase_line.price_subtotal / purchase_line.product_uom_qty
            price_invoice = purchase_line.product_uom._compute_price(
                price_invoice, self.product_uom
            )
            valuation_amount = price_invoice * abs(self.product_qty)
            company = self.location_id.company_id or self.env.company
            valuation_amount = purchase_line.order_id.currency_id._convert(
                valuation_amount, company.currency_id, company, self.date
            )
        return valuation_amount


    def _get_accounting_data_for_valuation(self):
        journal_id, acc_src, acc_dest, acc_valuation = super(
            StockMove, self
        )._get_accounting_data_for_valuation()
        if (
            self.company_id.romanian_accounting
            and self.product_id.categ_id.stock_account_change
        ):
            location_from = self.location_id
            location_to = self.location_dest_id
            valued_type = self.env.context.get("valued_type", "indefinite")

            # in nir si factura se ca utiliza 408
            if valued_type == "invoice_in_notice":
                if location_to.property_account_expense_location_id:
                    acc_dest = (
                        acc_valuation
                    ) = location_to.property_account_expense_location_id.id
                # if location_to.property_account_expense_location_id:
                #     acc_dest = (
                #         acc_valuation
                #     ) = location_to.property_account_expense_location_id.id
            elif valued_type == "invoice_out_notice":
                if location_to.property_account_income_location_id:
                    acc_valuation = acc_dest
                    acc_dest = location_to.property_account_income_location_id.id
                if location_from.property_account_income_location_id:
                    acc_valuation = location_from.property_account_income_location_id.id

            # in Romania iesirea din stoc de face de regula pe contul de cheltuiala
            elif valued_type in [
                "delivery_notice",
            ]:
                acc_dest = (
                    location_from.property_account_expense_location_id.id or acc_dest
                )
            elif valued_type in [
                "delivery_notice_return",
            ]:
                acc_src = location_to.property_account_expense_location_id.id or acc_src
        return journal_id, acc_src, acc_dest, acc_valuation
    
    # ================= Notice -> Invoice Methods =================
    
    def _get_invoice_from_notice_account_move(self):
        # Posibil sa avem mai multe linii stock.move de facturat, din picking-uri diferite
        # Unificam liniile doar daca avem acelasi cont
        account_move_product_ids = self.mapped("account_move_notice_id")
        values = {
            'amount':0, 
            'quantity': 0, 
            'accoutn_id': None, 
            'vat_account_id': None, 
            'vat':0, 
            'to_invoice':0
            }
        valued_type = None
        if self._is_delivery_notice() or self._is_delivery_notice_return():
            valued_type = "invoice_out_notice"
        if self._is_reception_notice() or self._is_reception_notice_return():
            valued_type = "invoice_in_notice"
        move = self.with_context(valued_type=valued_type)
        (
            journal_id,
            acc_src,
            acc_dest,
            acc_valuation,
            ) = move._get_accounting_data_for_valuation()
        acc_debit, acc_credit, tax = self._get_accounts_and_taxes(
            acc_dest,
            acc_valuation
            ) 
        for acc_move in account_move_product_ids:
            acc_move_line_ids = acc_move.line_ids
            line_product = acc_move_line_ids.filtered(lambda x: x.move_line_ids and x.account_id.id==acc_credit)
            line_op = acc_move_line_ids.filtered(lambda x: x.account_id.id == acc_debit)
            line_vat = acc_move_line_ids.filtered(lambda x: x.id not in  [line_product.id, line_op.id])
            if not values.get('account_id', None):
                values['account_id'] = line_op.account_id
                values['vat_account_id'] = line_vat.account_id
            if line_op.account_id != values.get('account_id') or (line_vat and line_vat.account_id !=values.get('vat_account_id')):
                # nu vom cumula valori din avize inregistrate in conturi diferite.
                continue
            values['amount'] += line_product.balance #valuation_amount
            values['quantity'] += line_product.quantity
            values['vat'] += line_vat.balance
            values['to_invoice'] += line_op.balance
        return values
        
    
    # ================= ORM Methods ===============================
    def write(self, vals):
        """
        User can update any picking in done state, but if this picking already
        invoiced the stock move done quantities can be different to invoice
        line quantities. So to avoid this inconsistency you can not update any
        stock move line in done state and have invoice lines linked.
        """
        if "product_uom_qty" in vals and not self.env.context.get(
            "bypass_stock_move_update_restriction"
        ):
            for move in self:
                if move.state == "done" and move.invoice_line_ids:
                    raise UserError(_("You can not modify an invoiced stock move"))
        return super().write(vals)

