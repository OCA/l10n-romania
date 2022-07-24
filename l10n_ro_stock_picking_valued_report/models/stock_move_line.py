# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    sale_line = fields.Many2one(
        related="move_id.sale_line_id", readonly=True, string="Related order line"
    )
    purchase_line = fields.Many2one(
        related="move_id.purchase_line_id", readonly=True, string="Related purchase line"
    )
    currency_id = fields.Many2one(
        compute="_compute_currency_id",
        )
    tax_id = fields.Many2many(
        compute="_compute_tax_price_unit", store=True, readonly=True
    )
    price_unit = fields.Float(
        compute="_compute_tax_price_unit", store=True, readonly=True
    )
    price_subtotal = fields.Monetary(
        compute="_compute_totals",
        currency_field="currency_id",
    )
    price_tax = fields.Monetary(
        compute="_compute_totals",
        currency_field="currency_id",
    )
    price_total = fields.Monetary(
        compute="_compute_totals",
        compute_sudo=True,
        currency_field="currency_id",
    )
    subtotal_internal_consumption = fields.Float(
        compute="_compute_subtotal_internal_consumption"
    )

    def _compute_subtotal_internal_consumption(self):
        for line in self:
            unit_price = line._get_unit_price_internal_consumption()
            line.subtotal_internal_consumption = line.qty_done * unit_price

    def _compute_purchase_order_line_fields(self):
        """This is computed with sudo for avoiding problems if you don't have
        access to purchase orders (stricter warehouse users, inter-company
        records...).
        """
        for line in self:
            purchase_line = line.purchase_line
            price_unit = (
                purchase_line.price_subtotal / purchase_line.product_qty
                if purchase_line.product_qty
                else purchase_line.price_unit
            )
            if line.product_uom_id != purchase_line.product_uom:
                price_unit = purchase_line.product_uom._compute_price(price_unit, line.product_uom_id)
            taxes = line.purchase_tax_id.compute_all(
                price_unit=price_unit,
                currency=line.purchase_currency_id,
                quantity=(line.qty_done or line.product_qty),
                product=line.product_id,
                partner=purchase_line.order_id.partner_id,
            )
            if (
                purchase_line.company_id.tax_calculation_rounding_method
                == "round_globally"
            ):
                price_tax = sum(t.get("amount", 0.0) for t in taxes.get("taxes", []))
            else:
                price_tax = taxes["total_included"] - taxes["total_excluded"]
            line.update(
                {
                    "purchase_tax_description": ", ".join(
                        t.name or t.description for t in line.purchase_tax_id
                    ),
                    "purchase_price_subtotal": taxes["total_excluded"],
                    "purchase_price_tax": price_tax,
                    "purchase_price_total": taxes["total_included"],
                }
            )

    def _compute_purchase_price_unit(self):
        for line in self:
            purchase_line = line.purchase_line
            line.purchase_price_unit = purchase_line.price_unit
            if line.product_uom_id != purchase_line.product_uom:
                line.purchase_price_unit = purchase_line.product_uom._compute_price(
                    purchase_line.price_unit, line.product_uom_id
                )

    def _get_aggregated_product_quantities(self, **kwargs):
        if self.picking_id.purchase_id:
            aggregated_move_lines = {}
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

                if line_key not in aggregated_move_lines:
                    aggregated_move_lines[line_key] = {
                        "name": name,
                        "description": description,
                        "qty_done": move_line.qty_done,
                        "product_uom": uom.name,
                        "product": move_line.product_id,
                        # added by us
                        "purchase_price_unit": round(move_line.purchase_price_unit, 2),
                        "purchase_tax_description": move_line.purchase_tax_description,
                        "purchase_price_subtotal": move_line.purchase_price_subtotal,
                        "purchase_price_tax": round(move_line.purchase_price_tax, 2),
                    }
                else:
                    aggregated_move_lines[line_key]["qty_done"] += move_line.qty_done
                    # added by us
                    aggregated_move_lines[line_key][
                        "purchase_price_subtotal"
                    ] += move_line.purchase_price_subtotal
                    aggregated_move_lines[line_key][
                        "purchase_price_tax"
                    ] += move_line.purchase_price_tax

            return aggregated_move_lines
        elif self.picking_id.is_internal_consumption:
            aggregated_move_lines = {}
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

                if line_key not in aggregated_move_lines:
                    aggregated_move_lines[line_key] = {
                        "name": name,
                        "description": description,
                        "qty_done": move_line.qty_done,
                        "product_uom": uom.name,
                        "product": move_line.product_id,
                        # added by us
                        "price_internal_consumption": round(
                            move_line._get_unit_price_internal_consumption(), 2
                        ),
                        "subtotal_internal_consumption": round(
                            move_line.subtotal_internal_consumption, 2
                        ),
                    }
                else:
                    aggregated_move_lines[line_key]["qty_done"] += move_line.qty_done
                    # added by us
                    aggregated_move_lines[line_key][
                        "subtotal_internal_consumption"
                    ] += move_line.subtotal_internal_consumption

            return aggregated_move_lines
        else:
            installed = (
                self.env["ir.module.module"]
                .sudo()
                .search(
                    [
                        ("name", "=", "stock_picking_report_valued"),
                        ("state", "=", "installed"),
                    ]
                )
            )
            if installed:
                return super()._get_aggregated_product_quantities(**kwargs)
        return {}

    def _get_unit_price_internal_consumption(self):
        if self.move_id._is_internal_transfer():
            pl = self.move_id.picking_id.partner_id.property_product_pricelist
            partner_price = self.move_id.product_id.lst_price
            if pl:
                partner_price = pl.price_get(
                    self.move_id.product_id.id, self.move_id.product_qty
                )[pl.id]
            return partner_price
        elif self.move_id._is_consumption() or self.move_id._is_consumption_return():
            avg = 0
            if self.move_id.stock_valuation_layer_ids:
                avg = sum(
                    [
                        svl.quantity * svl.unit_cost
                        for svl in self.move_id.stock_valuation_layer_ids
                    ]
                ) / sum(
                    [svl.quantity for svl in self.move_id.stock_valuation_layer_ids]
                )
            return avg
        return 0
