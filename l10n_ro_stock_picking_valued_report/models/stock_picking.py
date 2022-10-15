# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "l10n.ro.mixin"]

    l10n_ro_currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_l10n_ro_valued_fields",
        string="Currency",
        compute_sudo=True,  # See explanation for sudo in compute method,
    )
    l10n_ro_amount_untaxed = fields.Monetary(
        compute="_compute_l10n_ro_valued_fields",
        string="Untaxed Amount",
        compute_sudo=True,  # See explanation for sudo in compute method,
        currency_field="l10n_ro_currency_id",
    )
    l10n_ro_amount_tax = fields.Monetary(
        compute="_compute_l10n_ro_valued_fields",
        string="Taxes",
        compute_sudo=True,
        currency_field="l10n_ro_currency_id",
    )
    l10n_ro_amount_total = fields.Monetary(
        compute="_compute_l10n_ro_valued_fields",
        string="Total",
        compute_sudo=True,
        currency_field="l10n_ro_currency_id",
    )
    l10n_ro_is_internal = fields.Boolean(compute="_compute_l10n_ro_is_internal")

    def _compute_l10n_ro_is_internal(self):
        for pick in self:
            pick.l10n_ro_is_internal = pick.move_lines and not (
                pick.move_lines.mapped("sale_line_id")
                or pick.move_lines.mapped("purchase_line_id")
            )

    @api.depends(
        "state",
        "move_line_ids",
        "move_line_ids.qty_done",
        "move_line_ids.l10n_ro_price_subtotal",
        "move_line_ids.l10n_ro_price_total",
    )
    def _compute_l10n_ro_valued_fields(self):
        for pick in self:
            pick.l10n_ro_currency_id = (
                pick.move_line_ids[0].l10n_ro_currency_id
                if pick.move_line_ids
                else pick.company_id.currency_id
            )
            pick.l10n_ro_amount_untaxed = 0
            pick.l10n_ro_amount_tax = 0
            pick.l10n_ro_amount_total = 0
            for line in pick.move_line_ids:
                pick.l10n_ro_amount_untaxed += line.l10n_ro_price_subtotal
                pick.l10n_ro_amount_tax += line.l10n_ro_price_tax
                pick.l10n_ro_amount_total += line.l10n_ro_price_total
