# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class StockMoveLine(models.Model):
    _name = "stock.move.line"
    _inherit = ["stock.move.line", "l10n.ro.mixin"]

    l10n_ro_sale_line_id = fields.Many2one(
        related="move_id.sale_line_id", readonly=True, string="Related order line"
    )
    l10n_ro_purchase_line_id = fields.Many2one(
        related="move_id.purchase_line_id",
        readonly=True,
        string="Related purchase line",
    )
    l10n_ro_currency_id = fields.Many2one(
        "res.currency", compute="_compute_l10n_ro_valued_fields", readonly=True
    )
    l10n_ro_price_unit = fields.Float(
        compute="_compute_l10n_ro_valued_fields", readonly=True
    )
    l10n_ro_price_subtotal = fields.Monetary(
        compute="_compute_l10n_ro_valued_fields",
        readonly=True,
        currency_field="l10n_ro_currency_id",
    )
    l10n_ro_price_tax = fields.Monetary(
        compute="_compute_l10n_ro_valued_fields",
        readonly=True,
        currency_field="l10n_ro_currency_id",
    )
    l10n_ro_price_total = fields.Monetary(
        compute="_compute_l10n_ro_valued_fields",
        readonly=True,
        currency_field="l10n_ro_currency_id",
    )
    l10n_ro_additional_charges = fields.Monetary(
        compute="_compute_l10n_ro_valued_fields",
        readonly=True,
        currency_field="l10n_ro_currency_id",
    )

    def _get_aggregated_product_quantities(self, **kwargs):
        agg_move_lines = super()._get_aggregated_product_quantities(**kwargs)

        for aggregated_move_line in agg_move_lines:
            agg_move_lines[aggregated_move_line]["currency"] = (
                self.env.company.currency_id.id
            )
            agg_move_lines[aggregated_move_line]["l10n_ro_price_unit"] = 0
            agg_move_lines[aggregated_move_line]["l10n_ro_additional_charges"] = 0
            agg_move_lines[aggregated_move_line]["l10n_ro_price_subtotal"] = 0
            agg_move_lines[aggregated_move_line]["l10n_ro_price_tax"] = 0
            agg_move_lines[aggregated_move_line]["l10n_ro_price_total"] = 0
        for move_line in self:
            aggregated_properties = move_line._get_aggregated_properties(
                move_line=move_line
            )
            line_key = aggregated_properties["line_key"]
            agg_line = agg_move_lines[line_key]
            agg_line["l10n_ro_currency_id"] = move_line.l10n_ro_currency_id.id
            agg_line["l10n_ro_price_unit"] += move_line.l10n_ro_price_unit
            agg_line["l10n_ro_additional_charges"] += (
                move_line.l10n_ro_additional_charges
            )
            agg_line["l10n_ro_price_subtotal"] += move_line.l10n_ro_price_subtotal
            agg_line["l10n_ro_price_tax"] += move_line.l10n_ro_price_tax
            agg_line["l10n_ro_price_total"] += move_line.l10n_ro_price_total
        return agg_move_lines

    def _get_move_line_quantity(self):
        return self.quantity or self.reserved_qty

    def _get_l10n_ro_values_from_sale_line(self):
        self.ensure_one()
        sale_line = self.l10n_ro_sale_line_id
        move_qty = self._get_move_line_quantity()
        price_unit = (
            (sale_line.price_subtotal / sale_line.product_uom_qty)
            if sale_line.product_uom_qty
            else 0
        )
        price_unit_converted = sale_line.product_uom_id._compute_price(
            price_unit, sale_line.product_id.uom_id
        )
        price_subtotal = move_qty * price_unit_converted
        price_tax = (
            (sale_line.price_tax / sale_line.product_uom_qty) * move_qty
            if sale_line.product_uom_qty
            else 0
        )
        price_total = (
            (sale_line.price_total / sale_line.product_uom_qty) * move_qty
            if sale_line.product_uom_qty
            else 0
        )
        return {
            "l10n_ro_currency_id": sale_line.currency_id.id,
            "l10n_ro_price_unit": price_unit_converted,
            "l10n_ro_price_subtotal": price_subtotal,
            "l10n_ro_price_tax": price_tax,
            "l10n_ro_price_total": price_total,
            "l10n_ro_additional_charges": 0,
        }

    def _get_l10n_ro_values_from_purchase_line(self):
        self.ensure_one()
        purchase_line = self.l10n_ro_purchase_line_id
        move_values = self._get_l10n_ro_values_from_stock_move()
        if purchase_line.tax_ids:
            taxes = purchase_line.tax_ids.compute_all(
                move_values.get("l10n_ro_price_subtotal", 0),
                self.company_id.currency_id,
                1.0,
                product=purchase_line.product_id,
            )
            price_tax = taxes["total_included"] - taxes["total_excluded"]
            move_values["l10n_ro_price_tax"] = price_tax
            move_values["l10n_ro_price_total"] += price_tax
        if purchase_line.currency_id != self.company_id.currency_id:
            move_values = {
                key: self.company_id.currency_id._convert(
                    value,
                    purchase_line.currency_id,
                    self.company_id,
                    self.date,
                )
                for key, value in move_values.items()
                if key
                in [
                    "l10n_ro_price_unit",
                    "l10n_ro_price_subtotal",
                    "l10n_ro_price_tax",
                    "l10n_ro_price_total",
                    "l10n_ro_additional_charges",
                ]
            }
        return move_values

    def _get_l10n_ro_values_from_stock_move(self):
        self.ensure_one()
        move_qty = self._get_move_line_quantity()
        stock_move = self.move_id
        currency = self.company_id.currency_id
        sm_value = stock_move._get_value_data(add_extra_value=False)
        sm_value_with_extra = stock_move._get_value_data(add_extra_value=True)
        if not sm_value.get("quantity"):
            return {}
        value = sm_value.get("value", 0.0)
        price_unit = value / sm_value["quantity"]
        extra_value = sm_value_with_extra.get("value", 0.0)
        additional_charges = (extra_value - value) / sm_value["quantity"] * move_qty
        return {
            "l10n_ro_currency_id": currency.id,
            "l10n_ro_price_unit": price_unit,
            "l10n_ro_price_subtotal": move_qty * price_unit,
            "l10n_ro_price_tax": 0.0,
            "l10n_ro_price_total": move_qty * price_unit,
            "l10n_ro_additional_charges": additional_charges,
        }

    @api.depends(
        "l10n_ro_sale_line_id",
        "l10n_ro_purchase_line_id",
        "quantity",
        "picking_id.state",
        "move_id",
        "move_id.value",
    )
    def _compute_l10n_ro_valued_fields(self):
        for line in self:
            line_values = {
                "l10n_ro_currency_id": line.company_id.currency_id.id,
                "l10n_ro_price_unit": 0,
                "l10n_ro_price_subtotal": 0,
                "l10n_ro_price_tax": 0,
                "l10n_ro_price_total": 0,
                "l10n_ro_additional_charges": 0,
            }
            if line.l10n_ro_sale_line_id:
                sale_line_values = line._get_l10n_ro_values_from_sale_line()
                line_values.update(sale_line_values)
            elif line.l10n_ro_purchase_line_id:
                purchase_line_values = line._get_l10n_ro_values_from_purchase_line()
                line_values.update(purchase_line_values)
            else:
                stock_move_values = line._get_l10n_ro_values_from_stock_move()
                line_values.update(stock_move_values)
            line.update(line_values)
