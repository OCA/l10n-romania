# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


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

    def _get_move_line_quantity(self):
        return self.quantity or self.reserved_qty

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
            move_qty = line._get_move_line_quantity()
            line.l10n_ro_additional_charges = 0
            if line.l10n_ro_sale_line_id:
                sale_line = line.l10n_ro_sale_line_id
                line.l10n_ro_currency_id = sale_line.currency_id
                price_unit = (
                    (sale_line.price_subtotal / sale_line.product_uom_qty)
                    if sale_line.product_uom_qty
                    else 0
                )
                line.l10n_ro_price_unit = sale_line.product_uom._compute_price(
                    price_unit, line.product_uom_id
                )
                line.l10n_ro_price_subtotal = move_qty * line.l10n_ro_price_unit
                line.l10n_ro_price_tax = (
                    (sale_line.price_tax / sale_line.product_uom_qty) * move_qty
                    if sale_line.product_uom_qty
                    else 0
                )
                line.l10n_ro_price_total = (
                    (sale_line.price_total / sale_line.product_uom_qty) * move_qty
                    if sale_line.product_uom_qty
                    else 0
                )
            else:
                move = line.move_id or self.env["stock.move"]
                price_unit = 0.0
                additional_charges = 0.0

                if move and move.exists():
                    candidates = self.env["stock.move"]
                    candidates |= move

                    if hasattr(move, "move_orig_ids"):
                        candidates |= move.move_orig_ids
                    if hasattr(move, "move_dest_ids"):
                        candidates |= move.move_dest_ids


                    incoming = candidates.filtered(lambda m: m._is_in())

                    if incoming and incoming[0].picking_id and incoming[0].picking_id.picking_type_id:
                        if incoming[0].picking_id.picking_type_id.code == "internal":
                            incoming = incoming.filtered(lambda m: (m.product_uom_qty or 0) > 0)

                    total_qty = sum((m.product_uom_qty or 0.0) for m in incoming)
                    total_value = 0.0
                    for m in incoming:
                        mv = float(getattr(m, "value", 0.0) or getattr(m, "remaining_value", 0.0) or 0.0)
                        total_value += mv

                    if total_qty:
                        price_unit = total_value / total_qty

                    additional_charges = 0.0  

                line.l10n_ro_currency_id = line.company_id.currency_id
                line.l10n_ro_price_unit = price_unit
                line.l10n_ro_additional_charges = additional_charges
                line.l10n_ro_price_subtotal = move_qty * line.l10n_ro_price_unit

                line.l10n_ro_price_tax = 0
                if line.l10n_ro_purchase_line_id and move and move.exists():
                    purch = line.l10n_ro_purchase_line_id
                    if purch.product_uom_qty:
                        price_tax = (purch.price_tax / purch.product_uom_qty) * move_qty
                    else:
                        price_tax = purch.price_tax * move_qty
                    line.l10n_ro_price_tax = (
                        purch.currency_id._convert(
                            price_tax,
                            line.company_id.currency_id,
                            line.company_id,
                            line.date,
                        )
                    )
                line.l10n_ro_price_total = line.l10n_ro_price_subtotal + line.l10n_ro_price_tax


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
