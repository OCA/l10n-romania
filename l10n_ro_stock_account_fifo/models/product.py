# Copyright (C) 2022 Dakai Soft
# -*- coding: utf-8 -*-
from odoo import models
from odoo.tools import float_is_zero, float_repr


class ProductFifo(models.Model):
    _inherit = "product.product"
    
    # Adaptare din odoo.addons.stock_account.models.product
    def _prepare_out_svl_vals_ro(self, quantity, company):
        """Prepare the values for a stock valuation layer created by a delivery.

        :param quantity: the quantity to value, expressed in `self.uom_id`
        :return: values to use in a call to create
        :rtype: dict
        """
        self.ensure_one()
        company_id = self.env.context.get('force_company', self.env.company.id)
        company = self.env['res.company'].browse(company_id)
        currency = company.currency_id
        # Quantity is negative for out valuation layers.
        quantity = -1 * quantity
        vals_list = []
        vals_tpl = {
            'product_id': self.id,
            'value': currency.round(quantity * self.standard_price),
            'unit_cost': self.standard_price,
            'quantity': quantity,
        }
        if self.cost_method in ('average', 'fifo'):
            fifo_vals_list = self._run_fifo_ro(abs(quantity), company)
            for fifo_vals in fifo_vals_list:
                vals = vals_tpl.copy()
                vals['remaining_qty'] = fifo_vals.get('remaining_qty')
                # In case of AVCO, fix rounding issue of standard price when needed.
                if self.cost_method == 'average':
                    rounding_error = currency.round(self.standard_price * self.quantity_svl - self.value_svl)
                    if rounding_error:
                        # If it is bigger than the (smallest number of the currency * quantity) / 2,
                        # then it isn't a rounding error but a stock valuation error, we shouldn't fix it under the hood ...
                        if abs(rounding_error) <= (abs(quantity) * currency.rounding) / 2:
                            vals['value'] += rounding_error
                            vals['rounding_adjustment'] = '\nRounding Adjustment: %s%s %s' % (
                                '+' if rounding_error > 0 else '',
                                float_repr(rounding_error, precision_digits=currency.decimal_places),
                                currency.symbol
                            )
                if self.cost_method == 'fifo':
                    vals.update(fifo_vals)
                    # Blocam remaining quantity pe 0, astfel fifo_vacum nu mai reevalueaza
                    # TODO: de verificat
                    vals['remaining_qty'] = 0
                vals_list.append(vals)
        else:
            vals_list = [vals_tpl]
        return vals_list

    # Generic FIFO domain ce limiteaza cautarea la location_id ierarhic si lot_id
    def _prepare_domain_fifo(self, domain=[]):
        lot_id = loc_id = None
        if self._context.get('stock_move_line_id', None):
            stock_move_line = self._context.get('stock_move_line_id', None)
            
            if stock_move_line:
                if isinstance(stock_move_line, int):
                    stock_move_line = self.env['stock.move.line'].browse(stock_move_line)
                if isinstance(stock_move_line, models.Model):
                    loc_id =  stock_move_line.location_id
                    lot_id = stock_move_line.lot_id
        if loc_id:
            domain += [('stock_move_line_id.location_dest_id','child_of', loc_id.id)]
        if self.tracking in ['lot','serial'] and lot_id:
            domain += [('stock_move_line_id.lot_id','=',lot_id.id)]
        return domain

    # adaptare _run_fifo, de la return dict la return list dict_value.
    # pentru trasabilitate, pastram un cheia tracking sursa (int id) si cantitatea 
    # e safe sa avem aceste date cand se scad cantitatile luate din candidat..
    def _run_fifo_ro(self, quantity, company):
        self.ensure_one()

        # Find back incoming stock valuation layers (called candidates here) to value `quantity`.
        qty_to_take_on_candidates = quantity
        
        # folosim domeniul returnat de _prepare_domain_fifo
        # daca avem in context stock_move_line, atunci va filtra si dupa location si lot.
        domain = self._prepare_domain_fifo([
            ('product_id', '=', self.id),
            ]) + [
            ('remaining_qty', '>', 0),
            ('company_id', '=', company.id),
        ]
        models._logger.debug(f"Domeniu de cautare: {domain}")
        candidates = self.env['stock.valuation.layer'].sudo().search(domain)
        models._logger.debug(f"Candidati de cautare: {candidates}")
        new_standard_price = 0
        tmp_value = 0  # to accumulate the value taken on the candidates
        candidate_list = []
        for candidate in candidates:
            qty_taken_on_candidate = min(qty_to_take_on_candidates, candidate.remaining_qty)

            candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty
            new_standard_price = candidate_unit_cost
            value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
            value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
            new_remaining_value = candidate.remaining_value - value_taken_on_candidate

            candidate_vals = {
                'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                'remaining_value': new_remaining_value,
            }

            candidate.write(candidate_vals)
            track_svl = [(candidate.id, qty_taken_on_candidate, value_taken_on_candidate)]

            qty_to_take_on_candidates -= qty_taken_on_candidate
            tmp_value += value_taken_on_candidate

            # If there's still quantity to value but we're out of candidates, we fall in the
            # negative stock use case. We chose to value the out move at the price of the
            # last out and a correction entry will be made once `_fifo_vacuum` is called.
            vals = {
                    'value': -value_taken_on_candidate,
                    'unit_cost': new_standard_price,
                    'remaining_qty': -qty_taken_on_candidate,
                    'quantity': -qty_taken_on_candidate,
                }
            vals.update({'tracking':track_svl})
            candidate_list.append(vals)
            if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                #if float_is_zero(candidate.remaining_qty, precision_rounding=self.uom_id.rounding):
                #    next_candidates = candidates.filtered(lambda svl: svl.remaining_qty > 0)
                #    new_standard_price = next_candidates and next_candidates[0].unit_cost or new_standard_price
                break

        # Update the standard price with the price of the last used candidate, if any.
        if new_standard_price and self.cost_method == 'fifo':
            self.sudo().with_company(company.id).with_context(disable_auto_svl=True).standard_price = new_standard_price
        models._logger.debug(f"Candidates SVL {candidate_list}")
        return candidate_list

