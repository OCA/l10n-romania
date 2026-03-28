# Copyright (C) 2015 Deltatech
# Copyright (C) 2015 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _reconcile_account_move_lines(self, data):
        if self.company_id.l10n_ro_accounting:
            data["stock_output_lines"] = {}
        return super()._reconcile_account_move_lines(data)

    def _accumulate_amounts(self, data):
        data = super()._accumulate_amounts(data)
        if self.company_id.l10n_ro_accounting:
            amounts = {"amount": 0.0, "amount_converted": 0.0}
            # nu trebuie generate note contabile
            # pentru ca acestea sunt generate in miscarea de stoc
            data.update(
                {
                    "stock_expense": amounts,
                    "stock_return": amounts,
                    "stock_output": amounts,
                }
            )
        return data
