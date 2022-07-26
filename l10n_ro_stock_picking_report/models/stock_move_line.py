# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    sale_line_id = fields.Many2one(
        related="move_id.sale_line_id", readonly=True, string="Related order line"
    )
    purchase_line_id = fields.Many2one(
        related="move_id.purchase_line_id",
        readonly=True,
        string="Related purchase line",
    )
    currency_id = fields.Many2one(
        "res.currency", compute="_compute_valued_fields", readonly=True
    )
    price_unit = fields.Float(compute="_compute_valued_fields", readonly=True)
    price_subtotal = fields.Monetary(
        compute="_compute_valued_fields",
        readonly=True,
        currency_field="currency_id",
    )
    price_tax = fields.Monetary(
        compute="_compute_valued_fields",
        readonly=True,
        currency_field="currency_id",
    )
    price_total = fields.Monetary(
        compute="_compute_valued_fields",
        readonly=True,
        currency_field="currency_id",
    )

    def _get_move_line_quantity(self):
        return self.qty_done or self.product_qty

    @api.depends(
        "sale_line_id",
        "purchase_line_id",
        "qty_done",
        "picking_id.state",
        "move_id",
        "move_id.stock_valuation_layer_ids",
        "move_id.stock_valuation_layer_ids.value",
    )
    def _compute_valued_fields(self):
        for line in self:
            move_qty = line._get_move_line_quantity()
            if line.sale_line_id:
                sale_line = line.sale_line_id
                line.currency_id = sale_line.currency_id
                price_unit = (
                    (sale_line.price_subtotal / sale_line.product_uom_qty)
                    if sale_line.product_uom_qty
                    else 0
                )
                line.price_unit = sale_line.product_uom._compute_price(
                    price_unit, line.product_uom_id
                )
                line.price_subtotal = move_qty * line.price_unit
                line.price_tax = (
                    (sale_line.price_tax / sale_line.product_uom_qty) * move_qty
                    if sale_line.product_uom_qty
                    else 0
                )
                line.price_total = (
                    (sale_line.price_total / sale_line.product_uom_qty) * move_qty
                    if sale_line.product_uom_qty
                    else 0
                )
            else:
                svls = line.move_id.stock_valuation_layer_ids
                price_unit = 0
                if svls:
                    if svls[0].valued_type == "internal_transfer":
                        svls = svls.filtered(lambda s: s.quantity > 0)
                    if svls[0].stock_move_id._is_in():
                        svls = svls.filtered(lambda s: not s.stock_landed_cost_id)
                    price_unit = sum(svls.mapped("value")) / sum(
                        svls.mapped("quantity")
                    )
                line.currency_id = line.company_id.currency_id
                line.price_unit = price_unit
                line.price_subtotal = move_qty * line.price_unit
                line.price_tax = 0
                if line.purchase_line_id and svls:
                    price_tax = (
                        line.purchase_line_id.price_tax
                        / line.purchase_line_id.product_uom_qty
                        if line.purchase_line_id.product_uom_qty
                        else line.purchase_line_id.price_tax
                    ) * move_qty
                    line.price_tax = line.purchase_line_id.currency_id._convert(
                        price_tax,
                        line.company_id.currency_id,
                        line.company_id,
                        line.date,
                    )
                line.price_total = line.price_subtotal + line.price_tax

    def _get_aggregated_product_quantities(self, **kwargs):
        aggregated_move_lines = super()._get_aggregated_product_quantities(**kwargs)
        for aggregated_move_line in aggregated_move_lines:
            aggregated_move_lines[aggregated_move_line][
                "currency"
            ] = self.env.company.currency_id.id
            aggregated_move_lines[aggregated_move_line]["price_unit"] = 0
            aggregated_move_lines[aggregated_move_line]["price_subtotal"] = 0
            aggregated_move_lines[aggregated_move_line]["price_tax"] = 0
            aggregated_move_lines[aggregated_move_line]["price_total"] = 0

        for move_line in self:
            name = move_line.product_id.display_name
            description = move_line.move_id.description_picking
            if description == name or description == move_line.product_id.name:
                description = False
            uom = move_line.product_uom_id
            line_key = (
                str(move_line.product_id.id)
                + "_"
                + name
                + (description or "")
                + "uom "
                + str(uom.id)
            )
            aggregated_move_lines[line_key]["currency_id"] = move_line.currency_id.id
            aggregated_move_lines[line_key]["price_unit"] += move_line.price_unit
            aggregated_move_lines[line_key][
                "price_subtotal"
            ] += move_line.price_subtotal
            aggregated_move_lines[line_key]["price_tax"] += move_line.price_tax
            aggregated_move_lines[line_key]["price_total"] += move_line.price_total
        return aggregated_move_lines
