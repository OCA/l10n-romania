# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _inherit = "product.category"

    hide_stock_in_out_account = fields.Boolean(
        compute="_compute_hide_accounts",
        help="Only for Romania, to hide stock_input and stock_output "
        "accounts because they are the same as stock_valuation account",
    )
    stock_account_change = fields.Boolean(
        string="Allow stock account change from locations",
        help="Only for Romania, to change the accounts to the ones defined "
        "on stock locations",
    )

    @api.depends("name")
    def _compute_hide_accounts(self):
        for record in self:
            record.hide_stock_in_out_account = self.env.company.romanian_accounting

    @api.constrains(
        "property_stock_valuation_account_id",
        "property_stock_account_output_categ_id",
        "property_stock_account_input_categ_id",
    )
    def _check_valuation_accouts(self):
        """Overwrite default constraint for Romania,
        stock_valuation, stock_output and stock_input
        are the same
        """
        if self.env.company.romanian_accounting:
            # is a romanian company:
            for record in self:
                stock_input = record.property_stock_account_input_categ_id
                stock_output = record.property_stock_account_output_categ_id
                stock_val = record.property_stock_valuation_account_id
                if not (stock_input == stock_output == stock_val):
                    raise UserError(
                        _(
                            "For Romanian Stock Accounting the stock_input, "
                            "stock_output and stock_valuation accounts must "
                            "bethe same for category %s" % record.name
                        )
                    )
        else:
            super(ProductCategory, self)._check_valuation_accouts()

    @api.onchange(
        "property_stock_valuation_account_id",
        "property_stock_account_output_categ_id",
        "property_stock_account_input_categ_id",
    )
    def _onchange_stock_accounts(self):
        """only for Romania, stock_valuation output and input are the same"""
        for record in self:
            if record.hide_stock_in_out_account:
                # is a romanian company:
                record.property_stock_account_input_categ_id = (
                    record.property_stock_valuation_account_id
                )
                record.property_stock_account_output_categ_id = (
                    record.property_stock_valuation_account_id
                )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    property_stock_valuation_account_id = fields.Many2one(
        "account.account",
        "Stock Valuation Account",
        company_dependent=True,
        domain="[('company_id', '=', allowed_company_ids[0]),"
        "('deprecated', '=', False)]",
        check_company=True,
        help="In Romania accounting is only one account for valuation/input/"
        "output. If this value is set, we will use it, otherwise will "
        "use the category value. ",
    )

    def _get_product_accounts(self):
        accounts = super(ProductTemplate, self)._get_product_accounts()

        company = (
            self.env["res.company"].browse(self._context.get("force_company"))
            or self.env.company
        )
        if not company.romanian_accounting:
            return accounts

        property_stock_valuation_account_id = (
            self.property_stock_valuation_account_id
            or self.categ_id.property_stock_valuation_account_id
        )
        property_stock_usage_giving_account_id = (
            company.property_stock_usage_giving_account_id
        )
        if property_stock_valuation_account_id:
            accounts.update(
                {
                    "stock_input": property_stock_valuation_account_id,
                    "stock_output": property_stock_valuation_account_id,
                    "stock_valuation": property_stock_valuation_account_id,
                }
            )

        valued_type = self.env.context.get("valued_type", "indefinite")
        _logger.debug(valued_type)

        # in Romania iesirea din stoc de face de regula pe contul de cheltuiala
        if valued_type in [
            "delivery",
            "consumption",
            "production_return",
            "minus_inventory",
            "usage_giving",
        ]:
            accounts["stock_output"] = accounts["expense"]

        # intrare in stoc
        elif valued_type in [
            "production",
            "consumption_return",
            "delivery_return",
            "usage_giving_return",
            "plus_inventory",
        ]:
            accounts["stock_input"] = accounts["stock_output"] = accounts["expense"]
        elif valued_type == "dropshipped":
            accounts["stock_output"] = accounts["expense"]

        # suplimentar la darea in consum mai face o nota contabila
        elif valued_type == "usage_giving_secondary":
            accounts["stock_output"] = property_stock_usage_giving_account_id
            accounts["stock_input"] = property_stock_usage_giving_account_id
            accounts["stock_valuation"] = property_stock_usage_giving_account_id
        return accounts


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _run_fifo(self, quantity, company):
        self.ensure_one()

        if not self._context.get("origin_return_candidates"):
            return super(ProductProduct, self)._run_fifo(quantity, company)

        candidates = (
            self.env["stock.valuation.layer"]
            .sudo()
            .browse(self._context["origin_return_candidates"])
        )
        qty_to_take_on_candidates = quantity
        new_standard_price = 0
        tmp_value = 0  # to accumulate the value taken on the candidates
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

                qty_to_take_on_candidates -= qty_taken_on_candidate
                tmp_value += value_taken_on_candidate
                if float_is_zero(
                    qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding
                ):
                    break

        # Update the standard price with the price of the last used candidate, if any.
        if new_standard_price and self.cost_method == "fifo":
            self.sudo().with_company(company.id).standard_price = new_standard_price

        # If there's still quantity to value but we're out of candidates, we fall in the
        # negative stock use case. We chose to value the out move at the price of the
        # last out and a correction entry will be made once `_fifo_vacuum` is called.
        vals = {}
        if float_is_zero(
            qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding
        ):
            vals = {
                "value": -tmp_value,
                "unit_cost": tmp_value / quantity,
            }
        else:
            self = self.with_context(origin_return_candidates=None)
            vals_rest = super(ProductProduct, self)._run_fifo(
                qty_to_take_on_candidates, company
            )
            value = -(tmp_value + abs(vals_rest["value"]))
            unit_cost = abs(value) / (quantity - abs(vals_rest.get("remaining_qty", 0)))
            if "remaining_qty" in vals_rest:
                vals.update(
                    value=value,
                    unit_cost=unit_cost,
                    remaining_qty=vals_rest["remaining_qty"],
                )
            else:
                vals.update(value=value, unit_cost=unit_cost)
        return vals
