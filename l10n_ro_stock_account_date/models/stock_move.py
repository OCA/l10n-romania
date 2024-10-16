# Copyright (C) 2022 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.exceptions import UserError


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "l10n.ro.mixin"]

    def l10n_ro_get_move_date(self):
        self.ensure_one()
        new_date = self._context.get("force_period_date")
        if not new_date:
            if self.picking_id:
                if self.picking_id.l10n_ro_accounting_date:
                    new_date = self.picking_id.l10n_ro_accounting_date
            elif self.is_inventory:
                new_date = self.date
            elif "raw_material_production_id" in self._fields:
                if self.raw_material_production_id:
                    new_date = self.raw_material_production_id.date_planned_start
                elif self.production_id:
                    new_date = self.production_id.date_planned_start
            if not new_date:
                new_date = fields.datetime.now()
        restrict_date_last_month = (
            self.company_id.l10n_ro_restrict_stock_move_date_last_month
        )
        restrict_date_future = self.company_id.l10n_ro_restrict_stock_move_date_future
        first_posting_date = last_posting_date = False
        if restrict_date_last_month:
            first_posting_date = date.today().replace(day=1) + relativedelta(months=-1)
            last_posting_date = (
                date.today().replace(day=1)
                - timedelta(days=1)
                + relativedelta(months=1)
            )
        if restrict_date_future:
            last_posting_date = date.today()
        if not first_posting_date and last_posting_date:
            if not (new_date.date() <= last_posting_date):
                raise UserError(
                    _(
                        "Cannot validate stock move due to date restriction."
                        "The date must be after %(last_posting_date)s"
                    )
                    % {
                        "last_posting_date": last_posting_date,
                    }
                )
            self.check_lock_date(self.date)
        if first_posting_date and last_posting_date:
            if not (first_posting_date <= new_date.date() <= last_posting_date):
                raise UserError(
                    _(
                        "Cannot validate stock move due to date restriction."
                        "The date must be between %(first_posting_date)s and "
                        "%(last_posting_date)s"
                    )
                    % {
                        "first_posting_date": first_posting_date,
                        "last_posting_date": last_posting_date,
                    }
                )
            self.check_lock_date(self.date)
        return new_date

    def _action_done(self, cancel_backorder=False):
        moves_todo = super()._action_done(cancel_backorder=cancel_backorder)
        for move in self.filtered("is_l10n_ro_record"):
            move.date = move.l10n_ro_get_move_date()
            move.move_line_ids.write({"date": move.date})
        return moves_todo

    def _trigger_assign(self):
        res = super()._trigger_assign()
        for move in self.filtered("is_l10n_ro_record"):
            move.date = move.l10n_ro_get_move_date()
        return res

    def _get_price_unit(self):
        stock_move = self
        if self.is_l10n_ro_record:
            val_date = self.l10n_ro_get_move_date()
            stock_move = self.with_context(force_period_date=val_date)
        return super(StockMove, stock_move)._get_price_unit()

    def _account_entry_move(self, qty, description, svl_id, cost):
        self.ensure_one()
        stock_move = self
        if self.is_l10n_ro_record:
            val_date = self.l10n_ro_get_move_date()
            stock_move = self.with_context(force_period_date=val_date)
        return super(StockMove, stock_move)._account_entry_move(
            qty, description, svl_id, cost
        )

    def check_lock_date(self, move_date):
        self.ensure_one()
        lock_date = self.company_id._get_user_fiscal_lock_date()
        if move_date.date() < lock_date:
            raise UserError(
                _("Cannot validate stock move due to account date restriction.")
            )
