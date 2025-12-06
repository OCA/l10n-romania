# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    def button_create_landed_costs(self):
        """Update account of the landed cost ine with the one from invoice line."""

        res = super().button_create_landed_costs()
        landed_cost = self.env["stock.landed.cost"].browse(res.get("res_id"))
        if self.is_l10n_ro_record and landed_cost:
            picking_invoice_ids = (
                self.line_ids.mapped("purchase_line_id")
                .mapped("order_id")
                .mapped("picking_ids")
            )
            picking_landed_cost_ids = (
                self.env["stock.landed.cost"]
                .search([("state", "=", "done")])
                .mapped("picking_ids")
            )
            landed_cost.picking_ids = picking_invoice_ids.filtered(
                lambda lin: lin not in picking_landed_cost_ids and lin.state == "done"
            )
            for line in landed_cost.cost_lines:
                invoice_line = self.line_ids.filtered(
                    lambda lin, line=line: lin.product_id == line.product_id
                )
                if invoice_line:
                    line.account_id = invoice_line[0].account_id
        return res
