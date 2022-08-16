# Copyright (C) 2022 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#).
from ast import literal_eval

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_view_stock_valuation_layers(self):
        self.ensure_one()
        domain = [("id", "in", self.stock_valuation_layer_ids.ids)]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock_account.stock_valuation_layer_action"
        )
        context = literal_eval(action["context"])
        context.update(self.env.context)
        context["no_at_date"] = True
        return dict(action, domain=domain, context=context)
