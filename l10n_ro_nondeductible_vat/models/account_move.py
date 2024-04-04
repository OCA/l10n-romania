# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import api, models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    @api.depends("move_type")
    def _compute_is_storno(self):
        res = super()._compute_is_storno()
        for move in self:
            if (
                move.company_id.account_storno
                and move.company_id.l10n_ro_accounting
                and move.move_type == "entry"
            ):
                move.is_storno = True
        return res
