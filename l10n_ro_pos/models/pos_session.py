# ©  2015-2021 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from collections import defaultdict

from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    # def _prepare_line(self, order_line):
    #     values = super()._prepare_line(order_line)
    #     product = order_line.product_id
    #     if product.categ_id.l10n_ro_stock_account_change:
    #         location = (
    #             order_line.order_id.config_id.picking_type_id.default_location_src_id
    #         )
    #         account_income = location.l10n_ro_property_account_income_location_id
    #         if account_income:
    #             values["income_account_id"] = account_income.id
    #     return values

    def _reconcile_account_move_lines(self, data):
        if self.company_id.l10n_ro_accounting:
            data["stock_output_lines"] = {}
        return super()._reconcile_account_move_lines(data)

    def _accumulate_amounts(self, data):
        def get_amounts():
            res = {"amount": 0.0, "amount_converted": 0.0}
            return res

        data = super()._accumulate_amounts(data)

        amounts = get_amounts

        if self.company_id.l10n_ro_accounting:
            # nu trebuie generate note contabile
            # pentru ca acestea sunt generate in miscarea de stoc
            data.update(
                {
                    "stock_expense": defaultdict(amounts),
                    "stock_return": defaultdict(amounts),
                    "stock_output": defaultdict(amounts),
                }
            )

        return data
