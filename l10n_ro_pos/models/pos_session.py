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
            # nu trebuie generate note contabile
            # pentru ca acestea sunt generate in miscarea de stoc.
            # In Odoo 19 cheile sunt dict-uri grupate pe cont (defaultdict),
            # consumate cu .items() => fiecare valoare trebuie sa fie un dict
            # {amount, amount_converted}. Le golim ca sa nu se genereze linii.
            #
            # IMPORTANT: trebuie golit si "stock_valuation". Core-ul O19 il
            # consuma separat in _create_stock_valuation_lines (apelat din
            # _create_account_move), iar contrapartida sa (stock_output) e deja
            # golita aici. Daca lasam "stock_valuation" populat, se genereaza o
            # linie de valorizare fara contrapartida => nota de inchidere iese
            # dezechilibrata exact cu costul marfii al comenzilor nefacturate.
            data.update(
                {
                    "stock_expense": {},
                    "stock_return": {},
                    "stock_output": {},
                    "stock_valuation": {},
                }
            )
        return data
