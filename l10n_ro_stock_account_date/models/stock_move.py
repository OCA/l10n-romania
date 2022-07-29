# Copyright (C) 2022 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def get_move_date(self):
        self.ensure_one()
        new_date = False
        if self.picking_id:
            if self.picking_id.accounting_date:
                new_date = self.picking_id.accounting_date
        elif self.is_inventory and self.date:
            new_date = self.date
        elif "raw_material_production_id" in self._fields:
            if self.raw_material_production_id:
                new_date = self.raw_material_production_id.date_planned_start
            elif self.production_id:
                new_date = self.production_id.date_planned_start
        if not new_date:
            new_date = fields.datetime.now()
        return new_date

    def _action_done(self, cancel_backorder=False):
        move_dates = {}
        for move in self.filtered(lambda m: m.is_inventory and m.date):
            move_dates[move.id] = move.date
        moves_todo = super()._action_done(cancel_backorder=cancel_backorder)
        for move in moves_todo:
            if not move.is_inventory:
                move.date = move.get_move_date()
            if move_dates.get(move.id):
                move.date = move_dates[move.id]
            move.stock_valuation_layer_ids.sudo().write({"create_date": move.date})
            move.account_move_ids.sudo().write({"date": move.date})
        return moves_todo

    def _trigger_assign(self):
        res = super()._trigger_assign()
        for move in self:
            if not move.is_inventory:
                move.date = move.get_move_date()
        return res

    def _get_price_unit(self):
        # Update price unit for purchases in different currencies with the
        # reception date.
        if self.picking_id.date and self.purchase_line_id:
            po_line = self.purchase_line_id
            order = po_line.order_id
            price_unit = po_line.price_unit
            if po_line.taxes_id:
                price_unit = po_line.taxes_id.with_context(round=False).compute_all(
                    price_unit,
                    currency=order.currency_id,
                    quantity=1.0,
                    product=po_line.product_id,
                    partner=order.partner_id,
                )["total_excluded"]
            if po_line.product_uom.id != po_line.product_id.uom_id.id:
                price_unit *= (
                    po_line.product_uom.factor / po_line.product_id.uom_id.factor
                )
            if order.currency_id != order.company_id.currency_id:
                price_unit = order.currency_id._convert(
                    price_unit,
                    order.company_id.currency_id,
                    self.company_id,
                    self.picking_id.accounting_date or fields.datetime.now(),
                    round=False,
                )
            self.write(
                {
                    "price_unit": price_unit,
                    "date": self.picking_id.accounting_date or fields.datetime.now(),
                }
            )
            return price_unit
        return super()._get_price_unit()

    def _account_entry_move(self, qty, description, svl_id, cost):
        self.ensure_one()
        val_date = self.get_move_date() or self.date
        self = self.with_context(force_period_date=val_date)
        return super(StockMove, self)._account_entry_move(
            qty, description, svl_id, cost
        )
