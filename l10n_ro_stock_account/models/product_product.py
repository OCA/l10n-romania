# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, fields, models
from odoo.tools import float_is_zero, float_repr

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["product.product", "l10n.ro.mixin"]

    @api.depends("stock_valuation_layer_ids")
    @api.depends_context("to_date", "company", "location_id")
    def _compute_value_svl(self):
        """Compute `value_svl` and `quantity_svl`.
        Overwrite to allow multiple prices per location
        """
        l10n_ro_records = self.filtered("is_l10n_ro_record")
        if self - l10n_ro_records:
            super(ProductProduct, self - l10n_ro_records)._compute_value_svl()

        if l10n_ro_records and self.env.context.get("location_id"):
            company_id = self.env.company.id
            domain = [
                ("product_id", "in", l10n_ro_records.ids),
                ("company_id", "=", company_id),
                ("remaining_qty", ">", 0),
                ("l10n_ro_location_dest_id", "=", self.env.context.get("location_id")),
            ]
            if self.env.context.get("to_date"):
                to_date = fields.Datetime.to_datetime(self.env.context["to_date"])
                domain.append(("create_date", "<=", to_date))
            groups = self.env["stock.valuation.layer"].read_group(
                domain, ["remaining_value:sum", "remaining_qty:sum"], ["product_id"]
            )
            products = self.browse()
            for group in groups:
                product = self.browse(group["product_id"][0])
                product.value_svl = self.env.company.currency_id.round(
                    group["remaining_value"]
                )
                product.quantity_svl = group["remaining_qty"]
                products |= product
            remaining = l10n_ro_records - products
            remaining.value_svl = 0
            remaining.quantity_svl = 0
        else:
            super()._compute_value_svl()

    def _prepare_out_svl_vals(self, quantity, company):
        # FOr Romania, prepare a svl vals list for each svl reserved
        if not self.is_l10n_ro_record:
            return super()._prepare_out_svl_vals(quantity, company)
        self.ensure_one()
        if not company:
            company_id = self.env.context.get("force_company", self.env.company.id)
            company = self.env["res.company"].browse(company_id)
        currency = company.currency_id
        # Quantity is negative for out valuation layers.
        quantity = -1 * quantity
        vals_list = []
        vals_tpl = {
            "product_id": self.id,
            "value": currency.round(quantity * self.standard_price),
            "unit_cost": self.standard_price,
            "quantity": quantity,
        }
        if self.cost_method in ("average", "fifo"):
            fifo_vals_list = self._run_fifo(abs(quantity), company)
            for fifo_vals in fifo_vals_list:
                vals = vals_tpl.copy()
                vals["remaining_qty"] = fifo_vals.get("remaining_qty")
                # In case of AVCO, fix rounding issue of standard price when needed.
                if self.cost_method == "average":
                    rounding_error = currency.round(
                        self.standard_price * self.quantity_svl - self.value_svl
                    )
                    if rounding_error:
                        # If it is bigger than the (smallest number of the
                        # currency * quantity) / 2, then it isn't a rounding error
                        # but a stock valuation error, we shouldn't fix it under the hood ...
                        if (
                            abs(rounding_error)
                            <= (abs(quantity) * currency.rounding) / 2
                        ):
                            vals["value"] += rounding_error
                            vals[
                                "rounding_adjustment"
                            ] = "\nRounding Adjustment: %s%s %s" % (
                                "+" if rounding_error > 0 else "",
                                float_repr(
                                    rounding_error,
                                    precision_digits=currency.decimal_places,
                                ),
                                currency.symbol,
                            )
                if self.cost_method == "fifo":
                    vals.update(fifo_vals)
                vals_list.append(vals)
        else:
            vals_list = [vals_tpl]
        return vals_list

    def _l10n_ro_prepare_domain_fifo(self, domain=None):
        if not domain:
            domain = []
        lot_id = loc_id = None
        if self._context.get("stock_move_line_id", None):
            stock_move_line = self._context.get("stock_move_line_id", None)

            if stock_move_line:
                if isinstance(stock_move_line, int):
                    stock_move_line = self.env["stock.move.line"].browse(
                        stock_move_line
                    )
                if isinstance(stock_move_line, models.Model):
                    loc_id = stock_move_line.location_id
                    lot_id = stock_move_line.lot_id
        if self.tracking in ["lot", "serial"] and lot_id:
            domain += [("l10n_ro_lot_ids", "in", lot_id.id)]
        if loc_id:
            domain += [("l10n_ro_location_dest_id", "child_of", loc_id.id)]
        return domain

    def _run_fifo(self, quantity, company):
        if not self.env["res.company"]._check_is_l10n_ro_record(company.id):
            return super(ProductProduct, self)._run_fifo(quantity, company)

        self.ensure_one()
        domain = self._l10n_ro_prepare_domain_fifo([("product_id", "=", self.id)]) + [
            ("remaining_qty", ">", 0),
            ("remaining_value", ">", 0),
            ("company_id", "=", company.id),
        ]
        if self.env.context.get("origin_return_candidates"):
            domain += [("id", "in", self.env.context["origin_return_candidates"])]
        candidates = self.env["stock.valuation.layer"].sudo().search(domain)
        qty_to_take_on_candidates = quantity
        new_standard_price = 0
        tmp_value = 0  # to accumulate the value taken on the candidates
        candidate_list = []
        for candidate in candidates:
            qty_taken_on_candidate = min(
                qty_to_take_on_candidates, candidate.remaining_qty
            )
            if candidate.remaining_qty:
                candidate_unit_cost = (
                    candidate.remaining_value / candidate.remaining_qty
                )
                new_standard_price = candidate_unit_cost
                value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
                value_taken_on_candidate = candidate.currency_id.round(
                    value_taken_on_candidate
                )
                new_remaining_value = (
                    candidate.remaining_value - value_taken_on_candidate
                )

                candidate_vals = {
                    "remaining_qty": candidate.remaining_qty - qty_taken_on_candidate,
                    "remaining_value": new_remaining_value,
                }

                candidate.write(candidate_vals)
                track_svl = [
                    (candidate.id, qty_taken_on_candidate, value_taken_on_candidate)
                ]
                qty_to_take_on_candidates -= qty_taken_on_candidate
                tmp_value += value_taken_on_candidate
                # If there's still quantity to value but we're out of candidates, we fall in the
                # negative stock use case. We chose to value the out move at the price of the
                # last out and a correction entry will be made once `_fifo_vacuum` is called.
                vals = {
                    "value": -value_taken_on_candidate,
                    "unit_cost": new_standard_price,
                    "remaining_qty": -qty_taken_on_candidate,
                    "quantity": -qty_taken_on_candidate,
                }
                vals.update({"tracking": track_svl})
                candidate_list.append(vals)
                if float_is_zero(
                    qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding
                ):
                    break

        # Update the standard price with the price of the last used candidate, if any.
        if new_standard_price and self.cost_method == "fifo":
            self.sudo().with_company(company.id).with_context(
                disable_auto_svl=True
            ).standard_price = new_standard_price

        return candidate_list
