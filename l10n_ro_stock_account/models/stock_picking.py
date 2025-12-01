# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import fields, models


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "l10n.ro.mixin"]

    l10n_ro_notice = fields.Boolean()
    l10n_ro_reception_in_progress = fields.Boolean()

    def action_l10n_ro_view_account_moves(self):
        self.ensure_one()
        acc_lines = self.move_ids.account_move_id.line_ids
        if not acc_lines:
            return {}
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move.line",
            "view_mode": "list,form",
            "domain": [("id", "in", acc_lines.ids)],
        }
