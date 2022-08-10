# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# Copyright (C) 2020 Dakai Soft
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models
from odoo.tools import float_is_zero
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _filter_svl_on_move_line(self, domain):
        origin_svls = self.env['stock.valuation.layer'].search(domain)
        return origin_svls
    
    def _create_track_svl(self, value_list, **kwargs):
        sudo_svl = self.env['stock.valuation.layer'].sudo()
        for index, value in enumerate(value_list):
            svl_value = sudo_svl._pre_process_value(value) #eliminam datele de tracking, filtram valorile SVL
            new_svl = sudo_svl.create(svl_value)
            new_svl._post_process(value) #executam post create pentru tracking
            sudo_svl |= new_svl
        return sudo_svl
    
    def _get_transfer_move_lines(self):
        res = self.env['stock.move.line']
        for move_line in self.move_line_ids:
            if move_line.owner_id and move_line.owner_id != move_line.company_id.partner_id:
                continue
            if move_line.location_id._should_be_valued() and move_line.location_dest_id._should_be_valued():
                res |= move_line
        return res

    
    # cred ca este mai bine sa generam doua svl - o intrare si o iesire
    def _create_internal_transfer_svl(self, forced_quantity=None):
        svls = self.env['stock.valuation.layer']
        for move in self.with_context(standard=True, valued_type="internal_transfer"):
            move = move.with_company(move.company_id.id)

            valued_move_lines = move._get_transfer_move_lines()
            for valued_move_line in valued_move_lines:
                valued_quantity = valued_move_line.product_uom_id._compute_quantity(
                    valued_move_line.qty_done, move.product_id.uom_id
                )
                if float_is_zero(
                    forced_quantity or valued_quantity,
                    precision_rounding=move.product_id.uom_id.rounding,
                ):
                    continue
                svl_vals_list = move.product_id._prepare_out_svl_vals_ro(
                    forced_quantity or valued_quantity, move.company_id
                )
                for svl_vals in svl_vals_list:
                    svl_vals.update(move._prepare_common_svl_vals())
                    if forced_quantity:
                        svl_vals["description"] = (
                            "Correction of %s (modification of past move)"
                            % move.picking_id.name
                            or move.name
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
                            "tracking": [(svls[-1].id, abs(svl_vals.get("quantity", 0)), abs(svl_vals.get("value", 0)))],
                        }
                    )
                    svls |= self._create_track_svl([new_svl_vals])
        return svls

    def _create_in_svl(self, forced_quantity=None):
        if self.env.context.get("standard") and self.company_id.romanian_accounting:
            svls = self.env['stock.valuation.layer']
            for move in self:
                move = move.with_company(move.company_id)
                valued_move_lines = move._get_in_move_lines()
                for valued_move_line in valued_move_lines:
                    valued_quantity = valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
                    origin_unit_cost = None
                    tracking = []
                    if move.origin_returned_move_id and move.origin_returned_move_id.sudo().stock_valuation_layer_ids:
                        move_with_context = move.with_context(stock_move_line_id=valued_move_line)
                        origin_domain = move_with_context.product_id._prepare_domain_fifo([('product_id', '=', valued_move_line.product_id.id)])
                        origin_domain = [
                            ('stock_move_line_id', 'in', move.origin_returned_move_id._get_in_move_lines().ids)
                            ] + origin_domain
                        origin_svls = move._filter_svl_on_move_line(origin_domain)
                        if origin_svls:
                            origin_unit_cost = origin_svls[0].unit_cost
                            tracking = [(origin_svls[0].id, valued_quantity, origin_unit_cost * valued_quantity)]
                    unit_cost = abs(origin_unit_cost or move._get_price_unit())  # May be negative (i.e. decrease an out move).
                    if move.product_id.cost_method == 'standard':
                        unit_cost = move.product_id.standard_price
                    svl_vals = move.product_id._prepare_in_svl_vals(forced_quantity or valued_quantity, unit_cost)
                    svl_vals.update(move._prepare_common_svl_vals())
                    svl_vals.update({
                        'stock_move_line_id': valued_move_line.id,
                        'tracking': tracking
                        })
                    if forced_quantity:
                        svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
                    svls |= self._create_track_svl([svl_vals])
            return svls
        else:
            return super(StockMove, self)._create_in_svl(forced_quantity=forced_quantity)

    def _create_out_svl(self, forced_quantity=None):
        if self.env.context.get("standard") and self.company_id.romanian_accounting:
            svls = self.env['stock.valuation.layer']
            for move in self:
                move = move.with_company(move.company_id)
                valued_move_lines = move._get_out_move_lines()
                for valued_move_line in valued_move_lines:
                    valued_quantity = valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
                    if float_is_zero(forced_quantity or valued_quantity, precision_rounding=move.product_id.uom_id.rounding):
                        continue
                    svl_vals_list = valued_move_line.product_id._prepare_out_svl_vals_ro(forced_quantity or valued_quantity, valued_move_line.company_id)
                    for svl_vals in svl_vals_list:
                        svl_vals.update(move._prepare_common_svl_vals())
                        svl_vals.update({
                            'stock_move_line_id': valued_move_line.id,
                            })
                        if forced_quantity:
                            svl_vals['description'] = 'Correction of %s (modification of past move)' % valued_move_line.picking_id.name or valued_move_line.name
                        svl_vals['description'] += svl_vals.pop('rounding_adjustment', '')
                        svls |= self._create_track_svl([svl_vals])
            return svls
        else:
            return super(StockMove, self)._create_out_svl(forced_quantity=forced_quantity)

