# Copyright (C) 2022 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import groupby


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "l10n.ro.mixin"]

    def _action_done(self, cancel_backorder=False):
        ro_moves = self.filtered("is_l10n_ro_record")
        moves_todo = self.env["stock.move"]
        if self - ro_moves:
            moves_todo |= super(StockMove, self - ro_moves)._action_done(
                cancel_backorder=cancel_backorder
            )
        for moves_date, move_ids in groupby(
            ro_moves, key=lambda move: move.l10n_ro_get_move_date()
        ):
            moves = self.env["stock.move"].concat(*move_ids)
            moves.check_lock_date(moves_date)
            moves_todo |= super(
                StockMove, moves.with_context(force_period_date=moves_date)
            )._action_done(cancel_backorder=cancel_backorder)
            moves._l10n_ro_update_accounting_date(moves_date)
        return moves_todo

    def l10n_ro_get_move_date(self):
        self.ensure_one()
        new_date = self.env.context.get("force_period_date")
        now = fields.Date.today()
        if not new_date:
            if self.picking_id.l10n_ro_accounting_date:
                new_date = self.picking_id.l10n_ro_accounting_date
            elif self.is_inventory:
                new_date = self.date
            elif "raw_material_production_id" in self._fields:
                if self.raw_material_production_id:
                    new_date = self.raw_material_production_id.date_start
                elif self.production_id:
                    new_date = self.production_id.date_start
            if not new_date:
                new_date = now
        return new_date

    def _l10n_ro_update_accounting_date(self, move_date):
        self.date = move_date
        self.move_line_ids.write({"date": move_date})

    def check_lock_date(self, move_date):
        for company in self.mapped("company_id"):
            moves = self.filtered(lambda m, comp=company: m.company_id == comp)
            moves._check_lock_date_single_company(company, move_date)

    def _check_lock_date_single_company(self, company, move_date):
        restrict_date_last_month = company.l10n_ro_restrict_stock_move_date_last_month
        now = fields.Date.today()
        last_posting_date = False
        if restrict_date_last_month:
            # Allow only dates from 1st of previous month till today
            last_posting_date = now.replace(day=1) - relativedelta(months=1)

        if isinstance(last_posting_date, datetime):
            last_posting_date = last_posting_date.date()
        if isinstance(move_date, datetime):
            move_date = move_date.date()

        if last_posting_date and move_date < last_posting_date:
            raise UserError(
                self.env._(
                    "Cannot validate stock move due to date restriction."
                    " The date must be after %(last_posting_date)s",
                    last_posting_date=last_posting_date,
                )
            )
        if move_date > now:
            raise UserError(
                self.env._(
                    "Cannot validate stock move due to date restriction."
                    " The date must be before %(last_posting_date)s",
                    last_posting_date=last_posting_date,
                )
            )
        lock = company._get_lock_date_violations(
            move_date, fiscalyear=True, sale=False, purchase=False, tax=True, hard=True
        )
        if lock:
            raise UserError(
                self.env._(
                    "Cannot validate stock move with accounting date %(move_date)s "
                    "as it falls within a locked fiscal period.",
                    move_date=move_date,
                )
            )
