# Copyright (C) 2022 Dakai Soft
# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools import float_is_zero


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    stock_valuation_ids = fields.One2many("stock.valuation.layer", "stock_move_line_id")
    
    def _create_track_svl(self, value_list, **kwargs):
        sudo_svl = self.env['stock.valuation.layer'].sudo()
        
        for index, value in enumerate(value_list):
            svl_value = sudo_svl._pre_process_value(value) #extragem datele de tracking, filtram valorile SVL
            new_svl = sudo_svl.create(svl_value)
            # if index % 2 == 1 and kwargs.get('type', None) == 'internal_transfer' and value.get('tracking'):
            #     value.update({
            #         'tracking': [(
            #             sudo_svl[-1].id,
            #             value.get('tracking')[0][1],
            #             )]
            #         }) 
            new_svl._post_process(value) #executam post create pentru tracking
            sudo_svl |= new_svl
        return sudo_svl
    
    def _post_process_svl_values(self, value, **kwargs):
        value.update(
            {
                'tracking': kwargs.get('tracking',[])
                }
            )
        return value
    
    # Overwrite din addons.stock_account.models.stock_move
    def _prepare_common_svl_vals(self):
        """When a `stock.valuation.layer` is created from a `stock.move`, we can prepare a dict of
        common vals.

        :returns: the common values when creating a `stock.valuation.layer` from a `stock.move`
        :rtype: dict
        """
        self.ensure_one()
        ref = self.move_id.reference
        values = self.move_id._prepare_common_svl_vals()
        values.update({
                'stock_move_line_id': self.id,
                'stock_move_id': self.move_id.id,
                'company_id': self.company_id.id,
                'product_id': self.product_id.id,
                'description': ref and '%s - %s' % (ref, self.product_id.name) or self.product_id.name,
            })
        return values
    
    def _filter_svl_on_move_line_by_domain(self, domain):
        domain = [('stock_move_line_id','in',self.ids)] + domain
        smvl = self.env['stock.valuation.layer'].search(domain)
        return smvl
    
    # Extract price unit from SVL
    def _get_price_unit_slv_peer(self):
        """ Returns the unit price to value this stock move """
        self.ensure_one()
        price_unit = self.move_id._get_price_unit()
        precision = self.env['decimal.precision'].precision_get('Product Price')
        specific_move_line = None
        # If the move is a return, use the original move's price unit.
        if self.move_id.origin_returned_move_id and self.move_id.origin_returned_move_id.sudo().stock_valuation_layer_ids:
            move_line_ids = self.move_id.origin_returned_move_id.move_line_ids
            specific_svl = move_line_ids.\
                _filter_svl_on_move_line_by_domain(self.with_context(stock_move_line_id=self).product_id._prepare_domain_fifo([('product_id', '=', self.product_id.id)]))
            specific_move_line = specific_svl.mapped("stock_move_line_id")
            if specific_svl and specific_move_line in move_line_ids:
                # Teoretic trebuie sa vina un singur pret.
                # Situatia in care avem mai multe linii cu acelasi produs, dar nu suntem in situatia loturilor, este problematica.
                # Solutia ar fi ca operatorul sa aleaga pretul de intrare, sau sa aleaga linia livrata.
                price_unit = specific_svl.mapped("unit_cost")[0]
        return (not float_is_zero(price_unit, precision) and price_unit or self.product_id.standard_price, specific_move_line)
    
    # Overwrite din addons.stock_account.models.stock_move
    def _create_in_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        svls = self.env['stock.valuation.layer']
        for valued_move_line in self:
            valued_move_line = valued_move_line.with_company(valued_move_line.company_id)
            valued_move_line = valued_move_line.with_context(stock_move_line_id=valued_move_line)
            valued_quantity = valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, valued_move_line.product_id.uom_id)
            unit_cost, orig_move_line = valued_move_line._get_price_unit_slv_peer()
            unit_cost = abs(unit_cost)  # May be negative (i.e. decrease an out move).
            if valued_move_line.product_id.cost_method == 'standard':
                unit_cost = valued_move_line.product_id.standard_price
            # Old method
            # svl_vals = valued_move_line.product_id._prepare_in_svl_vals(forced_quantity or valued_quantity, unit_cost)
            svl_vals_list = valued_move_line.product_id._prepare_in_svl_vals_ro(forced_quantity or valued_quantity, unit_cost)
            for svl_vals in svl_vals_list:
                if orig_move_line:
                    svl_vals = valued_move_line._post_process_svl_values(svl_vals, tracking=[
                        (orig_move_line.stock_valuation_ids[0].id, svl_vals.get('quantity'))
                        ])
                svl_vals.update(valued_move_line._prepare_common_svl_vals())
                if forced_quantity:
                    svl_vals['description'] = 'Correction of %s (modification of past move)' % valued_move_line.picking_id.name or valued_move_line.name
                svls |= self._create_track_svl([svl_vals])
        return svls

    # Overwrite din addons.stock_account.models.stock_move
    def _create_out_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        svls = self.env['stock.valuation.layer']
        for valued_move_line in self:
            valued_move_line = valued_move_line.with_company(valued_move_line.company_id)
            valued_move_line = valued_move_line.with_context(stock_move_line_id=valued_move_line)
            valued_quantity = valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, valued_move_line.product_id.uom_id)
            if float_is_zero(forced_quantity or valued_quantity, precision_rounding=valued_move_line.product_id.uom_id.rounding):
                continue
            # old Method
            # svl_vals = valued_move_line.product_id._prepare_out_svl_vals(forced_quantity or valued_quantity, valued_move_line.company_id)
            svl_vals_list = valued_move_line.product_id._prepare_out_svl_vals_ro(forced_quantity or valued_quantity, valued_move_line.company_id)
            for svl_vals in svl_vals_list:
                svl_vals.update(valued_move_line._prepare_common_svl_vals())
                if forced_quantity:
                    svl_vals['description'] = 'Correction of %s (modification of past move)' % valued_move_line.picking_id.name or valued_move_line.name
                svl_vals['description'] += svl_vals.pop('rounding_adjustment', '')
                svls |= self._create_track_svl([svl_vals])
        return svls
    
    # cred ca este mai bine sa generam doua svl - o intrare si o iesire
    # Overwrite din l10n_ro_stock_account.models.stock_move
    def _create_internal_transfer_svl(self, forced_quantity=None):
        
        svls = self.env['stock.valuation.layer']
        for valued_move_line in self.with_context(standard=True, valued_type="internal_transfer"):
            valued_move_line = valued_move_line.with_company(valued_move_line.company_id.id)
            valued_move_line = valued_move_line.with_context(stock_move_line_id=valued_move_line)
            
            valued_quantity = valued_move_line.product_uom_id._compute_quantity(
                valued_move_line.qty_done, valued_move_line.product_id.uom_id
            )
            
            if float_is_zero(
                forced_quantity or valued_quantity,
                precision_rounding=valued_move_line.product_id.uom_id.rounding,
            ):
                continue
            # Old Method
            #svl_vals = valued_move_line.product_id._prepare_out_svl_vals(
            svl_vals_list = valued_move_line.product_id._prepare_out_svl_vals_ro(
                forced_quantity or valued_quantity, valued_move_line.company_id
            )
            for svl_vals in svl_vals_list:
                svl_vals.update(valued_move_line._prepare_common_svl_vals())
                if forced_quantity:
                    svl_vals["description"] = (
                        "Correction of %s (modification of past move)"
                        % valued_move_line.move_id.picking_id.name
                        or valued_move_line.move_id.name
                    )
                svl_vals["description"] += svl_vals.pop("rounding_adjustment", "")
                svls |= self._create_track_svl([svl_vals])
    
                new_svl_vals = svl_vals.copy()
                new_svl_vals.update(
                    {
                        "quantity": abs(svl_vals.get("quantity", 0)),
                        "remaining_qty": abs(svl_vals.get("quantity", 0)),
                        "unit_cost": abs(svl_vals.get("unit_cost", 0)),
                        "value": abs(svl_vals.get("value", 0)),
                        "remaining_value": abs(svl_vals.get("value", 0)),
                        "tracking": [(svls[-1].id, abs(svl_vals.get("quantity", 0)))],
                    }
                )
                svls |= self._create_track_svl([new_svl_vals])
        return svls
