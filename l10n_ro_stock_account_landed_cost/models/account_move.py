# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


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
                    lambda lin, line: lin.product_id == line.product_id
                )
                if invoice_line:
                    line.account_id = invoice_line[0].account_id
        return res


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "l10n.ro.mixin"]

    @api.onchange("is_landed_costs_line")
    def _onchange_is_landed_costs_line(self):
        res = super()._onchange_is_landed_costs_line()
        if (
            self.move_id.is_l10n_ro_record
            and self.product_type == "service"
            and self.is_landed_costs_line
        ):
            accounts = self.product_id.product_tmpl_id._get_product_accounts()
            if self.move_id.move_type not in ("out_invoice", "out_refund"):
                self.account_id = accounts["expense"]
            else:
                self.account_id = accounts["income"]
        return res
