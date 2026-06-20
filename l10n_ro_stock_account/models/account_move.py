# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    l10n_ro_extra_stock_move_id = fields.Many2one(
        "stock.move",
        string="Romania - Extra Stock Move",
        readonly=True,
    )
    fifo_neg_origin_move_id = fields.Many2one(
        "stock.move",
        string="Source IN move for negative stock compensation",
        index="btree_not_null",
        readonly=True,
        copy=False,
        help="The incoming stock move that triggered this FIFO negative "
        "stock compensation accounting entry.",
    )

    def _stock_account_prepare_anglo_saxon_in_lines_vals(self):
        l10n_ro_moves = self.filtered(lambda m: m.company_id.l10n_ro_accounting)
        if l10n_ro_moves == self:
            return []
        return super(
            AccountMove, self - l10n_ro_moves
        )._stock_account_prepare_anglo_saxon_in_lines_vals()

    def _stock_account_prepare_realtime_out_lines_vals(self):
        # nu se mai face descarcarea de gestiune la facturare
        ro_invoices = self.filtered(lambda inv: inv.is_l10n_ro_record)
        return super(
            AccountMove, self - ro_invoices
        )._stock_account_prepare_realtime_out_lines_vals()

    def _compute_is_storno(self):
        # EXTENDS 'account' for Romania
        # Stock moves with 'return' type or plus_inventory are considered storno
        res = super()._compute_is_storno()
        for move in self:
            if move.is_l10n_ro_record:
                stock_moves = move.line_ids._get_stock_moves()
                if stock_moves and all(
                    "return" in (m.l10n_ro_move_type or "")
                    or m.l10n_ro_move_type == "plus_inventory"
                    for m in stock_moves
                ):
                    move.is_storno = True
        return res
