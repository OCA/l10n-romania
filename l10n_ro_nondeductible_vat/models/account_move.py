# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    def _compute_is_storno(self):
        res = super()._compute_is_storno()
        moves = self.filtered(
            lambda m: m.company_id.l10n_ro_accounting
            and m.company_id.account_storno
            and m.move_type == "entry"
            and self.env.context.get("default_move_type") == "entry"
        )
        moves.is_storno = True
        return res
