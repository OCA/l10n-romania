# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "l10n.ro.mixin"]

    def _get_price_unit(self):
        # se caculeaza preturl cu functia standard
        price_unit = super()._get_price_unit()

        self.ensure_one()
        if self.is_l10n_ro_record:
            self.env["decimal.precision"].precision_get("Product Price")
            # If the move is a return, use the original move's price unit.
            if (
                self.origin_returned_move_id
                and self.origin_returned_move_id.sudo().stock_valuation_layer_ids
            ):
                layers = self.origin_returned_move_id.sudo().stock_valuation_layer_ids
                quantity = sum(layers.mapped("quantity"))
                price_unit = (
                    sum(layers.mapped("value")) / quantity
                    if not float_is_zero(
                        quantity, precision_rounding=layers.uom_id.rounding
                    )
                    else 0
                )

        return price_unit

    # nu se mai face in mod automat evaluarea la intrare in stoc
    def _create_in_svl(self, forced_quantity=None):
        _logger.debug("SVL:%s" % self.env.context.get("valued_type", ""))
        svls = self.env["stock.valuation.layer"]
        l10n_ro_records = self.filtered("is_l10n_ro_record")
        if self - l10n_ro_records:
            svls = super(StockMove, self - l10n_ro_records)._create_in_svl(
                forced_quantity
            )
        if l10n_ro_records and self.env.context.get("standard"):
            # For Romania, create a valuation layer for each stock move line
            for move in l10n_ro_records:
                move = move.with_company(move.company_id)
                valued_move_lines = move._get_in_move_lines()
                if not valued_move_lines and forced_quantity:
                    unit_cost = abs(
                        move._get_price_unit()
                    )  # May be negative (i.e. decrease an out move).
                    if move.product_id.cost_method == "standard":
                        unit_cost = move.product_id.standard_price
                    svl_vals = move.product_id._prepare_in_svl_vals(
                        forced_quantity, unit_cost
                    )
                    svl_vals.update(move._prepare_common_svl_vals())
                    if forced_quantity:
                        svl_vals["description"] = (
                            "Correction of %s (modification of past move)"
                            % move.picking_id.name
                            or move.name
                        )
                    svls = self.env["stock.valuation.layer"].sudo().create(svl_vals)
                for valued_move_line in valued_move_lines:
                    move = move.with_context(stock_move_line_id=valued_move_line)
                    valued_quantity = valued_move_line.product_uom_id._compute_quantity(
                        valued_move_line.qty_done, move.product_id.uom_id
                    )
                    origin_unit_cost = None
                    tracking = []
                    if (
                        move.origin_returned_move_id
                        and move.origin_returned_move_id.sudo().stock_valuation_layer_ids
                    ):
                        origin_domain = move.product_id._l10n_ro_prepare_domain_fifo(
                            move.company_id,
                            [("product_id", "=", valued_move_line.product_id.id)],
                        )
                        origin_domain = [
                            (
                                "stock_move_line_id",
                                "in",
                                move.origin_returned_move_id._get_in_move_lines().ids,
                            )
                        ] + origin_domain
                        origin_svls = move._l10n_ro_filter_svl_on_move_line(
                            origin_domain
                        )
                        if origin_svls:
                            origin_unit_cost = origin_svls[0].unit_cost
                            tracking = [
                                (
                                    origin_svls[0].id,
                                    valued_quantity,
                                    origin_unit_cost * valued_quantity,
                                )
                            ]
                    unit_cost = abs(
                        origin_unit_cost or move._get_price_unit()
                    )  # May be negative (i.e. decrease an out move).
                    if move.product_id.cost_method == "standard":
                        unit_cost = move.product_id.standard_price
                    svl_vals = move.product_id._prepare_in_svl_vals(
                        forced_quantity or valued_quantity, unit_cost
                    )
                    svl_vals.update(move._prepare_common_svl_vals())
                    svl_vals.update(
                        {
                            "l10n_ro_stock_move_line_id": valued_move_line.id,
                            "l10n_ro_tracking": tracking,
                        }
                    )
                    if forced_quantity:
                        svl_vals["description"] = (
                            "Correction of %s (modification of past move)"
                            % move.picking_id.name
                            or move.name
                        )
                    svls |= self._l10n_ro_create_track_svl([svl_vals])
        return svls

    # nu se mai face in mod automat evaluarea la iserirea din stoc
    def _create_out_svl(self, forced_quantity=None):
        _logger.debug("SVL:%s" % self.env.context.get("valued_type", ""))
        svls = self.env["stock.valuation.layer"]
        l10n_ro_records = self.filtered("is_l10n_ro_record")
        if self - l10n_ro_records:
            svls = super(StockMove, self - l10n_ro_records)._create_out_svl(
                forced_quantity
            )
        if l10n_ro_records and self.env.context.get("standard"):
            # For Romania get a list of valuation layers, to keep traceability
            # for each incoming price
            for move in self:
                move = move.with_company(move.company_id)
                valued_move_lines = move._get_out_move_lines()
                for valued_move_line in valued_move_lines:
                    valued_move_line = valued_move_line.with_context(
                        stock_move_line_id=valued_move_line
                    )
                    move = move.with_context(stock_move_line_id=valued_move_line)
                    valued_quantity = valued_move_line.product_uom_id._compute_quantity(
                        valued_move_line.qty_done, move.product_id.uom_id
                    )
                    if float_is_zero(
                        forced_quantity or valued_quantity,
                        precision_rounding=move.product_id.uom_id.rounding,
                    ):
                        continue
                    svl_vals_list = valued_move_line.product_id._prepare_out_svl_vals(
                        forced_quantity or valued_quantity,
                        valued_move_line.company_id,
                    )
                    for svl_vals in svl_vals_list:
                        svl_vals.update(move._prepare_common_svl_vals())
                        svl_vals.update(
                            {
                                "l10n_ro_stock_move_line_id": valued_move_line.id,
                            }
                        )
                        if forced_quantity:
                            svl_vals["description"] = (
                                "Correction of %s (modification of past move)"
                                % valued_move_line.picking_id.name
                                or valued_move_line.name
                            )
                        svl_vals["description"] += svl_vals.pop(
                            "rounding_adjustment", ""
                        )
                        svls |= move._l10n_ro_create_track_svl([svl_vals])
        return svls

    def _create_delivery_return_svl(self, forced_quantity=None):
        # move = self.with_context(standard=True, valued_type="delivery_return")
        # return move._create_in_svl(forced_quantity)

        move = self.with_context(standard=True, valued_type="delivery_return")

        if not move.origin_returned_move_id.sudo().stock_valuation_layer_ids:
            return move._create_in_svl(forced_quantity)

        _logger.debug("SVL:delivery_return")
        svls = self.env["stock.valuation.layer"]
        l10n_ro_records = move.filtered("is_l10n_ro_record")
        if self - l10n_ro_records:
            svls = super(StockMove, self - l10n_ro_records)._create_in_svl(
                forced_quantity
            )

        # For Romania, create a valuation layer for each stock move line
        for move in l10n_ro_records:
            move = move.with_company(move.company_id)

            out_svls = []
            origin_svls = (
                move.origin_returned_move_id.sudo().stock_valuation_layer_ids.sorted(
                    lambda layer: layer.create_date, reverse=False
                )
            )
            for svl in origin_svls:
                out_svls.append(
                    {
                        "product_id": svl.product_id.id,
                        "quantity": -1 * svl.quantity - svl.l10n_ro_qty_returned,
                        "unit_cost": abs(svl.unit_cost),
                        "svl_id": svl.id,
                        "svl": svl,
                    }
                )

            valued_move_lines = move._get_in_move_lines()
            if not valued_move_lines and forced_quantity:
                svls |= move._create_in_svl(forced_quantity)
                continue

            for valued_move_line in valued_move_lines:
                move = move.with_context(stock_move_line_id=valued_move_line)
                valued_quantity = valued_move_line.product_uom_id._compute_quantity(
                    valued_move_line.qty_done, move.product_id.uom_id
                )

                for out_svl in out_svls:
                    if out_svl["quantity"] <= 0:
                        continue
                    if valued_quantity <= 0:
                        break

                    if valued_quantity > out_svl["quantity"]:
                        quantity = out_svl["quantity"]
                    else:
                        quantity = valued_quantity

                    out_svl["quantity"] -= quantity
                    out_svl["svl"].l10n_ro_qty_returned += quantity
                    valued_quantity -= quantity

                    unit_cost = out_svl["unit_cost"]
                    tracking = [
                        (
                            out_svl["svl_id"],
                            quantity,
                            unit_cost * quantity,
                        )
                    ]

                    if move.product_id.cost_method == "standard":
                        unit_cost = move.product_id.standard_price
                    svl_vals = move.product_id._prepare_in_svl_vals(quantity, unit_cost)
                    svl_vals.update(move._prepare_common_svl_vals())
                    svl_vals.update(
                        {
                            "l10n_ro_stock_move_line_id": valued_move_line.id,
                            "l10n_ro_tracking": tracking,
                        }
                    )

                    svls |= self._l10n_ro_create_track_svl([svl_vals])
        return svls

    def _create_internal_transit_in_svl(self, forced_quantity=None):
        """
        - Se creaza SVL prin metoda _create_out_svl, dar pastram remaining
        - SVL vor fi inregistrare cu - pe contul de gestiune de origine.
        """
        move = self.with_context(standard=True, valued_type="internal_transit_in")
        svls = move._create_out_svl(forced_quantity)
        for svl in svls:
            svl.write(
                {
                    "remaining_qty": abs(svl.quantity),
                    "remaining_value": abs(svl.value),
                }
            )
        return svls

    def _create_internal_transit_out_svl(self, forced_quantity=None):
        """
        - Se creaza SVL prin copiere, pastram remaining
        - Daca nu avem o inlantuire, si transportul este manual, iesirea de face fifo.
        - SVL vor fi inregistrare cu + pe contul de gestiune de destinatie.
        """
        svls = self.env["stock.valuation.layer"].sudo()
        moves = self.with_context(standard=True, valued_type="internal_transit_out")
        for move in moves:
            svls |= move._create_out_svl(forced_quantity)
            for _svl in svls:
                _svl.write(
                    {
                        "quantity": abs(_svl.quantity),
                        "value": abs(_svl.value),
                        "remaining_qty": abs(_svl.quantity),
                        "remaining_value": abs(_svl.value),
                    }
                )
        return svls

    # cred ca este mai bine sa generam doua svl - o intrare si o iesire
    def _create_internal_transfer_svl(self, forced_quantity=None):
        svls = self.env["stock.valuation.layer"]
        for move in self:
            move = move.with_context(standard=True, valued_type="internal_transfer")
            move = move.with_company(move.company_id.id)

            valued_move_lines = move.move_line_ids
            for valued_move_line in valued_move_lines:
                move = move.with_context(stock_move_line_id=valued_move_line)
                valued_quantity = valued_move_line.product_uom_id._compute_quantity(
                    valued_move_line.qty_done, move.product_id.uom_id
                )
                if float_is_zero(
                    forced_quantity or valued_quantity,
                    precision_rounding=move.product_id.uom_id.rounding,
                ):
                    continue
                svl_vals_list = move.product_id._prepare_out_svl_vals(
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
                    svl_vals["l10n_ro_stock_move_line_id"] = valued_move_line.id
                    svls |= self._l10n_ro_create_track_svl([svl_vals])

                    new_svl_vals = svl_vals.copy()
                    new_svl_vals.update(
                        {
                            "quantity": abs(svl_vals.get("quantity", 0)),
                            "remaining_qty": abs(svl_vals.get("quantity", 0)),
                            "unit_cost": abs(svl_vals.get("unit_cost", 0)),
                            "value": abs(svl_vals.get("value", 0)),
                            "remaining_value": abs(svl_vals.get("value", 0)),
                            "l10n_ro_tracking": [
                                (
                                    svls[-1].id,
                                    abs(svl_vals.get("quantity", 0)),
                                    abs(svl_vals.get("value", 0)),
                                )
                            ],
                        }
                    )
                    svls |= self._l10n_ro_create_track_svl([new_svl_vals])
        return svls

    def _l10n_ro_filter_svl_on_move_line(self, domain):
        origin_svls = self.env["stock.valuation.layer"].search(domain)
        return origin_svls

    def _l10n_ro_create_track_svl(self, value_list, **kwargs):
        sudo_svl = self.env["stock.valuation.layer"].sudo()

        for _index, value in enumerate(value_list):
            svl_value = sudo_svl._l10n_ro_pre_process_value(
                value
            )  # eliminam datele de tracking, filtram valorile SVL
            new_svl = sudo_svl.create(svl_value)
            new_svl._l10n_ro_post_process(value)  # executam post create pentru tracking
            sudo_svl |= new_svl
        return sudo_svl

    # In case of single move line update locations of the stock move
    def _action_done(self, cancel_backorder=False):
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        for mv in moves:
            if len(mv.move_line_ids) == 1:
                mv.location_id = mv.move_line_ids[0].location_id
                mv.location_dest_id = mv.move_line_ids[0].location_dest_id
        # Launch fifo vacuum also for internal transfer moves
        internal_transfer_moves = moves.filtered("is_l10n_ro_record").filtered(
            lambda m: m._is_internal_transfer()
        )
        products_to_vacuum = internal_transfer_moves.mapped("product_id")
        company = (
            internal_transfer_moves.mapped("company_id")
            and internal_transfer_moves.mapped("company_id")[0]
            or self.env.company
        )
        for product_to_vacuum in products_to_vacuum:
            product_to_vacuum._run_fifo_vacuum(company)
        return moves
