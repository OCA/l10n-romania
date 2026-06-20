# Copyright (C) 2025 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import Command, api, fields, models

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "l10n.ro.mixin"]

    # Partial composite index that backs the per-location FIFO stack lookup
    # (_run_fifo_get_stack). Cuts ~200ms searches down to ~3-5ms on large
    # histories. Partial WHERE keeps it small.
    _fifo_stack_idx = models.Index(
        "(product_id, location_dest_id, date DESC, id DESC) "
        "WHERE state = 'done' AND is_in = TRUE"
    )
    # Partial index for the negative-stock compensation lookup
    # (_fifo_neg_apply_compensation). Only OUT moves with pending > 0
    # are indexed (typically << total moves).
    _fifo_neg_pending_idx = models.Index(
        "(product_id, location_id, company_id, date, id) "
        "WHERE fifo_neg_pending_qty > 0 AND state = 'done'"
    )

    fifo_neg_pending_qty = fields.Float(
        string="Negative Stock Pending Qty",
        copy=False,
        readonly=True,
        help="Quantity from a FIFO outgoing move that was valued at "
        "standard_price because the location stack was empty. "
        "Compensated FIFO on the next incoming move for the same "
        "(product, location) pair.",
    )
    fifo_neg_origin_value = fields.Monetary(
        string="Negative Stock Initial Value",
        currency_field="company_currency_id",
        copy=False,
        readonly=True,
    )
    fifo_neg_compensation_move_ids = fields.One2many(
        "account.move",
        "fifo_neg_origin_move_id",
        string="Negative Stock Compensation Entries",
        readonly=True,
    )

    def _compute_remaining_qty(self):
        res = super()._compute_remaining_qty()
        ro_fifo_moves = self.filtered(
            lambda move: move.company_id.fifo_per_location
            and move.product_id.cost_method == "fifo"
            and not move.product_id.lot_valuated
        )
        if not ro_fifo_moves:
            return res
        # Share a request-scoped cache across the batch (e.g. list view
        # showing N moves of the same product/location). Reduces one
        # _run_fifo_get_stack call per (product, location) pair instead of
        # one per move. Without this, a 80-row view takes ~4s; with it,
        # under 0.5s for typical groupings.
        cache = self.env.context.get("fifo_stack_cache")
        if cache is None:
            cache = {}
            ro_fifo_moves = ro_fifo_moves.with_context(fifo_stack_cache=cache)
        # Prefetch the location-related fields used inside the loop in one
        # round-trip; avoids one DB hit per move.
        ro_fifo_moves.fetch(["location_dest_id", "product_id"])
        for move in ro_fifo_moves:
            move.remaining_qty = 0
            if move.location_dest_id._should_be_valued():
                location = move.location_dest_id
                remaining_by_product = move.product_id._get_remaining_moves_ro(
                    location=location
                )
                move.remaining_qty = remaining_by_product.get(move.product_id, {}).get(
                    move, 0
                )
        return res

    def search_remaining_qty(self, operator, value):
        """For companies with ``fifo_per_location``, iterate per location so
        the search result matches the per-location ``remaining_qty`` computed
        by ``_compute_remaining_qty``. Falls back to the base behavior for
        companies that use company-wide FIFO."""
        if operator != "=" or not isinstance(value, bool) or value is not True:
            return super().search_remaining_qty(operator, value)
        ro_companies = self.env.companies.filtered("fifo_per_location")
        if not ro_companies:
            return super().search_remaining_qty(operator, value)
        # Non-RO companies: keep base behavior on those
        other_companies = self.env.companies - ro_companies
        move_ids = []
        if other_companies:
            base_domain = super(
                StockMove, self.with_context(allowed_company_ids=other_companies.ids)
            ).search_remaining_qty(operator, value)
            # base returns [('id', 'in', ids)]
            if base_domain and isinstance(base_domain[0], tuple):
                move_ids += list(base_domain[0][2])

        # RO companies: iterate locations × products
        products = (
            "default_product_id" in self.env.context
            and self.env["product.product"].browse(
                self.env.context["default_product_id"]
            )
            or self.env["product.product"]
        )
        for company in ro_companies:
            company_products = products
            if not company_products:
                company_products = self.env["product.product"].search(
                    [("is_storable", "=", True), ("qty_available", ">", 0)]
                )
            locations = self.env["stock.location"].search(
                [
                    ("is_valued_internal", "=", True),
                    ("company_id", "=", company.id),
                ]
            )
            for location in locations:
                remaining = company_products.with_company(
                    company
                )._get_remaining_moves_ro(location=location)
                for qty_by_move in remaining.values():
                    move_ids.extend(m.id for m in qty_by_move)
        return [("id", "in", list(set(move_ids)))]

    @api.depends("value", "quantity", "product_id.stock_move_ids.value")
    def _compute_remaining_value(self):
        return super()._compute_remaining_value()

    def _action_done(self, cancel_backorder=False):
        ro_fifo_moves_out = self.filtered(
            lambda m: m._is_out()
            and m.product_id.cost_method == "fifo"
            and m.company_id.fifo_per_location
            and not m.product_id.lot_valuated
            and m.product_uom.compare(m.quantity, 0) != 0
        )
        res = super(StockMove, self - ro_fifo_moves_out)._action_done(
            cancel_backorder=cancel_backorder
        )
        if ro_fifo_moves_out:
            moves_out_fifo_splitted = ro_fifo_moves_out._split_for_fifo_assignment()
            for move in moves_out_fifo_splitted:
                move._set_quantity_done(move.quantity)
                move.picked = True
            res += super(
                StockMove, ro_fifo_moves_out + moves_out_fifo_splitted
            )._action_done(cancel_backorder=cancel_backorder)
        return res

    def _set_value(self, correction_quantity=None):
        ro_fifo_out_moves = self.filtered(
            lambda move: move.company_id.fifo_per_location
            and move._is_out()
            and move.product_id.cost_method == "fifo"
            and not move.product_id.lot_valuated
        )
        res = super(StockMove, self - ro_fifo_out_moves)._set_value(
            correction_quantity=correction_quantity
        )
        if ro_fifo_out_moves:
            for move in ro_fifo_out_moves:
                value = 0
                if move.value_manual:
                    move.value = move.value_manual
                    continue
                for move_line in move.move_line_ids:
                    value += move.product_id._run_fifo_value(
                        move_line.quantity_product_uom,
                        lot=move_line.lot_id,
                        at_date=move.date,
                        location=move_line.location_dest_id,
                    )
                move.value = value
        # AVG: mark outgoing moves that consumed more than the on-hand qty
        # at the source location, so they get compensated on the next IN.
        # For FIFO this is handled by the explicit split into FIFO layers.
        avg_out_moves = self.filtered(
            lambda m: m.company_id.fifo_per_location
            and m.company_id.fifo_location_negative_compensation
            and m._is_out()
            and m.product_id.cost_method == "average"
            and not m.product_id.lot_valuated
            and not m.fifo_neg_pending_qty
        )
        for move in avg_out_moves:
            product_at_loc = move.product_id.with_company(move.company_id).with_context(
                location=move.location_id.id
            )
            qty_avail_before = product_at_loc.qty_available
            valued_qty = move._get_valued_qty()
            if not valued_qty:
                continue
            # Deficit = how much of this OUT exceeded the on-hand stock at
            # the source. (qty_available is measured BEFORE state=done, so
            # it does not yet include this OUT's effect.)
            deficit = valued_qty - max(0, qty_avail_before)
            if move.product_id.uom_id.compare(deficit, 0) <= 0:
                continue
            unit_price = move.value / valued_qty if valued_qty else 0
            move.write(
                {
                    "fifo_neg_pending_qty": deficit,
                    "fifo_neg_origin_value": unit_price * deficit,
                }
            )
        # Negative stock compensation on incoming moves (FIFO and AVG).
        ins = self.filtered(
            lambda m: m.company_id.fifo_per_location
            and m.company_id.fifo_location_negative_compensation
            and m.is_in
            and m.product_id.cost_method in ("fifo", "average")
            and not m.product_id.lot_valuated
        )
        for move in ins:
            move._fifo_neg_apply_compensation()
        return res

    def _get_value_from_origin_move(
        self,
        quantity,
        forced_std_price=False,
        at_date=False,
        ignore_manual_update=False,
    ):
        if self.move_orig_ids:
            move_origin = self.move_orig_ids[0]
            origin_data = move_origin._get_value_data(
                forced_std_price=forced_std_price,
                at_date=at_date,
                ignore_manual_update=ignore_manual_update,
            )
            proportion = (
                quantity / origin_data["quantity"] if origin_data["quantity"] else 0
            )
            value = proportion * origin_data["value"]
            return {
                "value": value,
                "quantity": quantity,
                "description": self.env._(
                    "Value based on origin move %(reference)s",
                    reference=self.move_orig_ids.reference,
                ),
            }
        return {}

    def _get_value_from_std_price(self, quantity, std_price=False, at_date=None):
        res = super()._get_value_from_std_price(
            quantity=quantity, std_price=std_price, at_date=at_date
        )
        ro_fifo_move_with_origin = self.filtered(
            lambda move: move.company_id.fifo_per_location
            and move.product_id.cost_method == "fifo"
            and not move.product_id.lot_valuated
            and move.move_orig_ids
            and quantity
        )
        if ro_fifo_move_with_origin:
            res = ro_fifo_move_with_origin._get_value_from_origin_move(
                quantity=quantity, at_date=at_date
            )
        return res

    def _split_for_fifo_assignment(self):
        """Splits moves based on FIFO list coming from product _run_fifo."""
        fifo_split_vals_list = []
        for move in self:
            fifo_list = move.product_id.with_context(
                location=move.location_id.ids
            )._run_fifo(move.product_qty, location=move.location_id)
            quantity = move.product_qty
            while quantity >= move.quantity and fifo_list:
                fifo_split_vals_list, quantity = self._l10n_ro_process_fifo_split(
                    move, fifo_list, quantity, fifo_split_vals_list
                )
        if fifo_split_vals_list:
            fifo_splitted_moves = self.env["stock.move"].create(fifo_split_vals_list)
            fifo_splitted_moves.write({"state": "assigned"})
            return fifo_splitted_moves
        return self.env["stock.move"]

    @api.model
    def _l10n_ro_update_fifo_move(self, fifo_item, move):
        """Updates the move based on FIFO item."""
        if move:
            move._set_quantity_done(move.quantity)

    @api.model
    def _l10n_ro_process_fifo_split(
        self, move, fifo_list, quantity, fifo_split_vals_list
    ):
        """Processes the FIFO split for a given move."""
        fifo_item = fifo_list.pop(0)
        fifo_quantity = fifo_item["quantity"]
        if fifo_quantity < quantity:
            new_move_vals_list = move._split(fifo_quantity)
            new_move_vals_list[0].update(
                {
                    "value_manual": fifo_item["value"],
                    "price_unit": fifo_item["value"] / fifo_quantity,
                }
            )
            quantity -= fifo_quantity
            move.quantity = quantity
        else:
            quantity = 0
            move_vals = {
                "value_manual": fifo_item["value"] / fifo_quantity * move.quantity,
                "price_unit": fifo_item["value"] / fifo_quantity,
            }
            # No-split case: the whole move is on negative stock (forced value).
            # Mark it for compensation on the next incoming move.
            if (
                not fifo_item.get("move_id")
                and move.company_id.fifo_location_negative_compensation
            ):
                unit = fifo_item["value"] / fifo_quantity if fifo_quantity else 0
                move_vals["fifo_neg_pending_qty"] = move.quantity
                move_vals["fifo_neg_origin_value"] = unit * move.quantity
            move.write(move_vals)
            new_move_vals_list = []
        if fifo_item:
            move._l10n_ro_update_fifo_move(fifo_item, move)
        if new_move_vals_list:
            for new_move_vals in new_move_vals_list:
                self._l10n_ro_update_fifo_split_move_vals(
                    move, new_move_vals, fifo_item, fifo_quantity
                )
        fifo_split_vals_list += new_move_vals_list
        return fifo_split_vals_list, quantity

    @api.model
    def _l10n_ro_update_fifo_split_move_vals(
        self, move, new_move_vals, fifo_item, fifo_quantity
    ):
        """Updates the move vals for a FIFO split move."""
        new_move_vals["picking_id"] = move.picking_id.id
        new_move_vals["quantity"] = fifo_quantity
        new_move_vals["date"] = move.date
        # Mark split moves generated from a 'forced value' (negative stock on
        # the location) so they get compensated on the next incoming move.
        if (
            not fifo_item.get("move_id")
            and move.company_id.fifo_location_negative_compensation
        ):
            new_move_vals["fifo_neg_pending_qty"] = fifo_quantity
            new_move_vals["fifo_neg_origin_value"] = fifo_item["value"]

    # ------------------------------------------------------------------
    # Negative stock compensation
    # ------------------------------------------------------------------
    def _fifo_neg_apply_compensation(self):
        """Allocate the current incoming move's value over previous outgoing
        moves with ``fifo_neg_pending_qty > 0`` on the same
        (product, location_dest_id) pair and emit a correction accounting
        entry for the price difference.

        Idempotent: if this incoming move has already generated compensation
        entries (e.g. _set_value is re-called when the invoice is posted),
        we return immediately to avoid doubling the effect."""
        self.ensure_one()
        if self.fifo_neg_compensation_move_ids:
            return
        location = self.location_dest_id
        if not location._should_be_valued():
            return
        valued_qty = self._get_valued_qty()
        if not valued_qty or not self.value:
            return
        pending_moves = self.env["stock.move"].search(
            [
                ("product_id", "=", self.product_id.id),
                ("location_id", "=", location.id),
                ("company_id", "=", self.company_id.id),
                ("fifo_neg_pending_qty", ">", 0),
                ("state", "=", "done"),
                ("date", "<=", self.date),
            ],
            order="date, id",
        )
        if not pending_moves:
            return
        in_price = self.value / valued_qty
        remaining_in_qty = valued_qty
        line_vals = []
        for out_move in pending_moves:
            if remaining_in_qty <= 0:
                break
            consume_qty = min(out_move.fifo_neg_pending_qty, remaining_in_qty)
            if not consume_qty:
                continue
            unit_origin = (
                out_move.fifo_neg_origin_value / out_move.fifo_neg_pending_qty
                if out_move.fifo_neg_pending_qty
                else 0
            )
            old_value_for_qty = unit_origin * consume_qty
            new_value_for_qty = in_price * consume_qty
            delta = new_value_for_qty - old_value_for_qty
            out_move.write(
                {
                    "value": out_move.value + delta,
                    "fifo_neg_pending_qty": out_move.fifo_neg_pending_qty - consume_qty,
                    "fifo_neg_origin_value": out_move.fifo_neg_origin_value
                    - old_value_for_qty,
                }
            )
            remaining_in_qty -= consume_qty
            if self.company_id.currency_id.is_zero(delta):
                continue
            line_vals += self._fifo_neg_build_adjust_lines(out_move, delta)
        if not line_vals:
            return
        journal = self.company_id.account_stock_journal_id
        if not journal:
            _logger.warning(
                "FIFO compensation: missing stock journal on company %s",
                self.company_id.display_name,
            )
            return
        adjust = (
            self.env["account.move"]
            .sudo()
            .create(
                {
                    "ref": self.env._(
                        "Negative stock compensation %s",
                        self.reference or self.name,
                    ),
                    "journal_id": journal.id,
                    "date": fields.Date.context_today(self),
                    "fifo_neg_origin_move_id": self.id,
                    "line_ids": [Command.create(v) for v in line_vals],
                }
            )
        )
        adjust._post()
        return adjust

    def _fifo_neg_build_adjust_lines(self, out_move, delta):
        """Journal lines for the negative stock correction.
        delta > 0: the outgoing move was undervalued; we add the difference
                   to the variation/COGS account and credit the stock account.
        delta < 0: the outgoing move was overvalued; we invert the direction."""
        accounts = out_move.product_id._get_product_accounts()
        stock_acc = out_move.location_id.valuation_account_id or accounts.get(
            "stock_valuation"
        )
        variation_acc = accounts.get("stock_variation") or accounts.get("expense")
        if not stock_acc or not variation_acc:
            return []
        amount = abs(delta)
        label = self.env._(
            "FIFO location compensation: %(product)s / %(loc)s",
            product=out_move.product_id.display_name,
            loc=out_move.location_id.display_name,
        )
        debit_acc = variation_acc if delta > 0 else stock_acc
        credit_acc = stock_acc if delta > 0 else variation_acc
        return [
            {
                "account_id": debit_acc.id,
                "name": label,
                "debit": amount,
                "credit": 0,
                "product_id": out_move.product_id.id,
            },
            {
                "account_id": credit_acc.id,
                "name": label,
                "debit": 0,
                "credit": amount,
                "product_id": out_move.product_id.id,
            },
        ]
