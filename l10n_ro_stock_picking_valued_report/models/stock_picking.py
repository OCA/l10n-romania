# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_valued_fields",
        string="Currency",
        compute_sudo=True,  # See explanation for sudo in compute method,
    )
    amount_untaxed = fields.Monetary(
        compute="_compute_valued_fields",
        string="Untaxed Amount",
        compute_sudo=True,  # See explanation for sudo in compute method,
        currency_field="currency_id",
    )
    amount_tax = fields.Monetary(
        compute="_compute_valued_fields",
        string="Taxes",
        compute_sudo=True,
        currency_field="currency_id",
    )
    amount_total = fields.Monetary(
        compute="_compute_valued_fields",
        string="Total",
        compute_sudo=True,
        currency_field="currency_id",
    )
    is_internal = fields.Boolean(compute="_compute_is_internal")

    def _compute_is_internal(self):
        for pick in self:
            pick.is_internal = pick.move_lines and not (
                pick.move_lines.mapped("sale_line_id")
                or pick.move_lines.mapped("purchase_line_id")
            )

    @api.depends(
        "state",
        "move_line_ids",
        "move_line_ids.qty_done",
        "move_line_ids.price_subtotal",
        "move_line_ids.price_total",
    )
    def _compute_valued_fields(self):
        for pick in self:
            pick.currency_id = (
                pick.move_line_ids[0].currency_id
                if pick.move_line_ids
                else pick.company_id.currency_id
            )
            pick.amount_untaxed = 0
            pick.amount_tax = 0
            pick.amount_total = 0
            for line in pick.move_line_ids:
                pick.amount_untaxed += line.price_subtotal
                pick.amount_tax += line.price_tax
                pick.amount_total += line.price_total
