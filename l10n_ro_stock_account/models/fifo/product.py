# Copyright (C) 2025 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models
from odoo.fields import Domain

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["product.product", "l10n.ro.mixin"]

    def _compute_value(self):
        """Compute totals of multiple svl related values"""
        company_id = self.env.company
        self.company_currency_id = company_id.currency_id
        ro_fifo_products = self.filtered(
            lambda p: company_id.fifo_per_location
            and p.cost_method == "fifo"
            and not p.lot_valuated
        )
        res = super(ProductProduct, self - ro_fifo_products)._compute_value()
        # Share a request-scoped cache across all FIFO stack lookups in this
        # batch — reduces N SQL queries to 1 per (product, location).
        cache = self.env.context.get("fifo_stack_cache")
        if cache is None:
            cache = {}
            ro_fifo_products = ro_fifo_products.with_context(fifo_stack_cache=cache)
        for product in ro_fifo_products:
            at_date = fields.Datetime.to_datetime(product.env.context.get("to_date"))
            if at_date:
                product = product.with_context(at_date=at_date)
            qty_available = product.sudo(False)._with_valuation_context().qty_available
            product.total_value = product._run_fifo_value(
                qty_available, at_date=at_date
            )
            product.avg_cost = (
                product.total_value / qty_available if qty_available else 0
            )
        return res

    def _get_remaining_moves_ro(self, lot=None, at_date=None, location=None):
        """Returns a dictionary of stock moves and their remaining quantities
        for each product in self."""
        moves_qty_by_product = {}
        for product in self:
            if location:
                product = product.with_context(location=location.ids)
            moves, remaining_qty = product._run_fifo_get_stack(
                lot=lot, at_date=at_date, location=location
            )
            moves = self.env["stock.move"].concat(*moves)
            if not moves:
                continue
            qty_by_move = {m: m.quantity for m in moves[1:]}
            qty_by_move[moves[0]] = remaining_qty
            moves_qty_by_product[product] = qty_by_move
        return moves_qty_by_product

    def _get_cogs_value(self, quantity):
        ro_fifo_products = self.filtered(
            lambda p: self.env.company.fifo_per_location
            and p.cost_method == "fifo"
            and not p.lot_valuated
        )
        res = super(ProductProduct, self - ro_fifo_products)._get_cogs_value(quantity)
        ro_fifo_products._run_fifo_value(quantity)
        return res

    def _run_fifo_value(self, quantity, lot=None, at_date=None, location=None):
        """Returns the total value for the next outgoing product base on the
        qty give as argument."""
        fifo_list = self._run_fifo(
            quantity, lot=lot, at_date=at_date, location=location
        )
        total_value = sum(item["value"] for item in fifo_list)
        return total_value

    def _run_fifo(self, quantity, lot=None, at_date=None, location=None):
        """Returns the value for the next outgoing product base on the qty
        give as argument."""
        self.ensure_one()
        ro_fifo_products = self.filtered(
            lambda p: self.env.company.fifo_per_location
            and p.cost_method == "fifo"
            and not p.lot_valuated
        )
        if not ro_fifo_products:
            return super()._run_fifo(
                quantity, lot=lot, at_date=at_date, location=location
            )
        if self.uom_id.compare(quantity, 0) <= 0:
            return [
                {
                    "move_id": False,
                    "quantity": quantity,
                    "value": quantity * self.standard_price,
                    "description": self.env._(
                        "Forced value for %(qty)s units", qty=quantity
                    ),
                }
            ]

        fifo_list = []
        remaining_moves = self._get_remaining_moves_ro(
            lot=lot, at_date=at_date, location=location
        ).get(self, {})
        fifo_stack = sorted(remaining_moves.keys(), key=lambda sm: (sm.date, sm.id))
        # Going up to get the quantity in the argument
        while quantity > 0 and fifo_stack:
            move = fifo_stack.pop(0)
            move_values = {
                "move_id": move.id,
                "quantity": move.remaining_qty,
                "value": move.remaining_value,
                "description": move.display_name,
            }
            if at_date:
                move_values = move._get_value_data(at_date=at_date)
                move_values["move_id"] = move.id
            rem_qty = move_values["quantity"]
            move_value = move_values["value"]
            if rem_qty >= quantity:
                reserved_qty = min(quantity, rem_qty)
                fifo_list.append(
                    {
                        "move_id": move.id,
                        "quantity": reserved_qty,
                        "value": move_value * reserved_qty / rem_qty,
                        "description": move.display_name,
                    }
                )
                quantity -= reserved_qty
            else:
                fifo_list.append(move_values)
                quantity -= move_values["quantity"]
        # When we required more quantity than available we extrapolate
        # with the last known price
        if quantity > 0:
            fifo_list.append(
                {
                    "move_id": False,
                    "quantity": quantity,
                    "value": quantity * self.standard_price,
                    "description": self.env._(
                        "Forced value for %(qty)s units", qty=quantity
                    ),
                }
            )
        return fifo_list

    def _run_fifo_get_stack(self, lot=None, at_date=None, location=None):
        ro_fifo_products = self.filtered(
            lambda p: self.env.company.fifo_per_location
            and p.cost_method == "fifo"
            and not p.lot_valuated
        )
        if not ro_fifo_products:
            return super()._run_fifo_get_stack(
                lot=lot, at_date=at_date, location=location
            )

        # Request-scoped cache. Callers (reports, batched _compute_value)
        # can pre-populate ``fifo_stack_cache={}`` in context to share
        # results across many (product, location) lookups.
        cache = self.env.context.get("fifo_stack_cache")
        cache_key = None
        if cache is not None:
            cache_key = (
                self.id,
                location.id if location else None,
                lot.id if lot else None,
                at_date,
            )
            if cache_key in cache:
                return cache[cache_key]

        external_location = location and location.is_valued_external
        fifo_stack = []
        fifo_stack_size = 0
        if location:
            # ``strict=True`` keeps qty_available counted at this exact
            # location only (not its descendants). Without it, a parent
            # location like WH1/Stock would see its sublocations' quantities
            # and over-state the FIFO stack — and a transfer Stock→Sub-A
            # would consume from the parent's stack twice (once for the
            # transfer itself, then again when subsequent operations re-walk
            # the parent's inflated stack).
            self = self.with_context(  # noqa: PLW0642
                location=location.ids, strict=True
            )
            fifo_stack_size = self.with_context(to_date=at_date).qty_available
        elif lot:
            fifo_stack_size = lot.product_qty
        else:
            fifo_stack_size = (
                self._with_valuation_context()
                .with_context(to_date=at_date)
                .qty_available
            )
        # Use UoM rounding for the comparison so fractional quantities
        # (kg, m, etc.) are handled correctly.
        if self.uom_id.compare(fifo_stack_size, 0) <= 0:
            return fifo_stack, 0

        moves_domain = Domain(
            [
                ("product_id", "=", self.id),
                ("company_id", "=", self.env.company.id),
                ("state", "=", "done"),
            ]
        )
        if lot:
            moves_domain &= Domain([("move_line_ids.lot_id", "in", lot.id)])
        if at_date:
            moves_domain &= Domain([("date", "<=", at_date)])
        if location:
            moves_domain &= Domain([("location_dest_id", "=", location.id)])
        if external_location:
            moves_domain &= Domain([("is_out", "=", True)])
        else:
            moves_domain &= Domain([("is_in", "=", True)])
        # Base limit to 100 to avoid issue with other UoM than Unit
        initial_limit = max(int(fifo_stack_size) * 10, 100)
        moves_in = self.env["stock.move"].search(
            moves_domain, order="date desc, id desc", limit=initial_limit
        )
        # Prefetch move_line_ids + the fields used by _get_valued_qty so we
        # don't hit the DB once per move in the walk below. Eliminates N
        # round-trips on stacks with many incoming moves (~95% speedup on
        # cold caches with 500+ moves).
        if moves_in:
            moves_in.move_line_ids.fetch(
                [
                    "quantity_product_uom",
                    "picked",
                    "owner_id",
                    "location_id",
                    "location_dest_id",
                    "lot_id",
                ]
            )
        remaining_qty_on_first_stack_move = 0
        current_offset = 0
        idx = 0
        # Go to the bottom of the stack. Iterate by index instead of slicing
        # the recordset (recordset slicing creates a new recordset each step,
        # so the legacy approach was O(N^2) over the stack walk).
        while self.uom_id.compare(fifo_stack_size, 0) > 0 and idx < len(moves_in):
            move = moves_in[idx]
            idx += 1
            in_qty = move._get_valued_qty()
            fifo_stack.append(move)
            remaining_qty_on_first_stack_move = min(in_qty, fifo_stack_size)
            fifo_stack_size -= in_qty
            if self.uom_id.compare(fifo_stack_size, 0) > 0 and idx >= len(moves_in):
                # We need to fetch more moves
                current_offset += 1
                moves_in = self.env["stock.move"].search(
                    moves_domain,
                    order="date desc, id desc",
                    offset=current_offset * initial_limit,
                    limit=initial_limit,
                )
                if moves_in:
                    moves_in.move_line_ids.fetch(
                        [
                            "quantity_product_uom",
                            "picked",
                            "owner_id",
                            "location_id",
                            "location_dest_id",
                            "lot_id",
                        ]
                    )
                idx = 0
        fifo_stack.reverse()
        result = (fifo_stack, remaining_qty_on_first_stack_move)
        if cache is not None and cache_key is not None:
            cache[cache_key] = result
        return result
