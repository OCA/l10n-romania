# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "l10n.ro.mixin"]

    def _get_accounting_data_for_valuation(self):
        (
            journal_id,
            acc_src,
            acc_dest,
            acc_valuation,
        ) = super()._get_accounting_data_for_valuation()
        if (
            self.is_l10n_ro_record
            and self.purchase_line_id.order_id.l10n_ro_reception_in_progress
        ):
            account = self.env["account.account"].browse(acc_src)
            if account.l10n_ro_reception_in_progress_account_id:
                acc_src = account.l10n_ro_reception_in_progress_account_id.id
        return journal_id, acc_src, acc_dest, acc_valuation

    def _account_entry_move(self, qty, description, svl_id, cost):
        if (
            self.is_l10n_ro_record
            and self.picking_id.purchase_id.l10n_ro_reception_in_progress
        ):
            self = self.with_context(l10n_ro_reception_in_progress=True)
        res = super()._account_entry_move(qty, description, svl_id, cost)
        return res
