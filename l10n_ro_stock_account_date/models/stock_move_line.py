# Copyright (C) 2022 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class StockMoveLine(models.Model):
    _name = "stock.move.line"
    _inherit = ["stock.move.line", "l10n.ro.mixin"]

    def _action_done(self):
        res = super()._action_done()
        ro_recs = self.exists().filtered("is_l10n_ro_record")
        for move_line in ro_recs:
            if move_line.move_id:
                move_line.date = move_line.move_id.l10n_ro_get_move_date()
        return res
