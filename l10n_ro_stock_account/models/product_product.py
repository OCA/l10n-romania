# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, fields, models
from odoo.tools import float_compare, float_is_zero, float_repr
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["product.product", "l10n.ro.mixin"]

    @api.depends("stock_valuation_layer_ids")
    @api.depends_context("to_date", "company", "location_id", "lot_id")
    def _compute_value_svl(self):
        """Compute `value_svl` and `quantity_svl`.
        Overwrite to allow multiple prices per location
        """
        get_param = self.env["ir.config_parameter"].sudo().get_param

        simple_valuation = get_param("l10n_ro_stock_account.simple_valuation", "False")
        simple_valuation = safe_eval(simple_valuation)
        l10n_ro_records = self.filtered("is_l10n_ro_record")
        if simple_valuation:
            l10n_ro_records = l10n_ro_records.filtered(
                lambda r: r.cost_method != "average"
            )
        res = super(ProductProduct, self - l10n_ro_records)._compute_value_svl()

        if l10n_ro_records:
            company = self.env.company
            use_svl_lot_config = (
                company.l10n_ro_stock_account_svl_lot_allocation
                or self.env.context.get("force_svl_lot_config", False)
            )
            domain_ctx = []
            if self.env.context.get("location_id"):
                domain_ctx = [
                    (
                        "l10n_ro_location_dest_id",
                        "=",
                        self.env.context.get("location_id"),
                    )
                ]
            if use_svl_lot_config and self.env.context.get("lot_id"):
                domain_ctx += [
                    (
                        "l10n_ro_lot_ids",
                        "in",
                        [self.env.context.get("lot_id")],
                    )
                ]
            domain = [
                ("product_id", "in", l10n_ro_records.ids),
                ("company_id", "=", company.id),
            ] + domain_ctx

            if self.env.context.get("to_date"):
                to_date = fields.Datetime.to_datetime(self.env.context["to_date"])
                domain.append(("create_date", "<=", to_date))
            else:
                domain.append(("remaining_qty", ">", 0))
            groups = self.env["stock.valuation.layer"].read_group(
                domain,
                [
                    "value:sum",
                    "quantity:sum",
                    "remaining_value:sum",
                    "remaining_qty:sum",
                ],
                ["product_id"],
            )
            products = self.browse()
            for group in groups:
                product = self.browse(group["product_id"][0])
                if self.env.context.get("to_date"):
                    product.value_svl = self.env.company.currency_id.round(
                        group["value"]
                    )
                    product.quantity_svl = group["quantity"]
                else:
                    product.value_svl = self.env.company.currency_id.round(
                        group["remaining_value"]
                    )
                    product.quantity_svl = group["remaining_qty"]

                products |= product
            remaining = l10n_ro_records - products
            remaining.value_svl = 0
            remaining.quantity_svl = 0
        return res

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
            if isinstance(fifo_vals_list, dict):
                fifo_vals_list = [fifo_vals_list]
            for fifo_vals in fifo_vals_list:
                vals = vals_tpl.copy()
                vals["quantity"] = fifo_vals.get("quantity", 0)
                vals["value"] = fifo_vals.get("value", 0)
                vals["remaining_qty"] = fifo_vals.get("remaining_qty", 0)
                vals["l10n_ro_tracking"] = fifo_vals.get("l10n_ro_tracking")

                # In case of AVCO, fix rounding issue of standard price when needed.
                if self.cost_method == "average" and not self.env.context.get(
                    "origin_return_candidates"
                ):
                    vals["value"] = currency.round(
                        vals["quantity"] * self.standard_price
                    )
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

                if self.cost_method == "fifo" or (
                    self.cost_method == "average"
                    and self.env.context.get("origin_return_candidates")
                ):
                    vals.update(fifo_vals)
                vals_list.append(vals)
        else:
            vals_list = [vals_tpl]
        return vals_list

    def _l10n_ro_prepare_domain_fifo(self, company, domain=None):
        if company is None:
            company = self.env.company

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

        use_svl_lot_config = company.l10n_ro_stock_account_svl_lot_allocation
        if self.tracking in ["lot", "serial"] and lot_id and use_svl_lot_config:
            domain += [("l10n_ro_lot_ids", "in", [lot_id.id])]
        if loc_id:
            domain += [("l10n_ro_location_dest_id", "child_of", loc_id.id)]
        return domain

    def _run_fifo(self, quantity, company):
        # get_param = self.env["ir.config_parameter"].sudo().get_param
        # simple_valuation = get_param("l10n_ro_stock_account.simple_valuation", "False")
        # simple_valuation = safe_eval(simple_valuation)
        # if simple_valuation and self.cost_method == "average":
        #     return super(ProductProduct, self)._run_fifo(quantity, company)

        if not self.env["res.company"]._check_is_l10n_ro_record(company.id):
            return super(ProductProduct, self)._run_fifo(quantity, company)

        self.ensure_one()
        domain = [
            ("product_id", "=", self.id),
            ("remaining_qty", ">", 0),
            ("company_id", "=", company.id),
        ]
        domain = self._l10n_ro_prepare_domain_fifo(company, domain)
        if self.env.context.get("origin_return_candidates"):
            domain += [("id", "in", self.env.context["origin_return_candidates"])]
        candidates = self.env["stock.valuation.layer"].sudo().search(domain)
        qty_to_take_on_candidates = quantity
        new_standard_price = 0
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
                for linked_svl in candidate.stock_valuation_layer_ids:
                    track_svl += [(linked_svl.id, 0, 0)]

                qty_to_take_on_candidates -= qty_taken_on_candidate
                # If there's still quantity to value but we're out of candidates, we fall in the
                # negative stock use case. We chose to value the out move at the price of the
                # last out and a correction entry will be made once `_fifo_vacuum` is called.
                vals = {
                    "value": -value_taken_on_candidate,
                    "unit_cost": new_standard_price,
                    "quantity": -qty_taken_on_candidate,
                }
                vals.update({"l10n_ro_tracking": track_svl})
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

        if not float_is_zero(
            qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding
        ):
            assert qty_to_take_on_candidates > 0
            last_fifo_price = new_standard_price or self.standard_price
            negative_stock_value = last_fifo_price * -qty_to_take_on_candidates
            tmp_value = abs(negative_stock_value)
            vals = {
                "quantity": -qty_to_take_on_candidates,
                "remaining_qty": -qty_to_take_on_candidates,
                "value": -tmp_value,
                "unit_cost": last_fifo_price,
            }
            candidate_list.append(vals)
        return candidate_list

    def _run_fifo_vacuum(self, company=None):
        """Compensate layer valued at an estimated price with the price of future receipts
        if any. If the estimated price is equals to the real price, no layer is created but
        the original layer is marked as compensated.
        It will be done for each stock location.

        :param company: recordset of `res.company` to limit the execution of the vacuum
        """

        # get_param = self.env["ir.config_parameter"].sudo().get_param
        # simple_valuation = get_param("l10n_ro_stock_account.simple_valuation", "False")
        # simple_valuation = safe_eval(simple_valuation)
        # if simple_valuation and self.cost_method == "average":
        #     return super(ProductProduct, self)._run_fifo_vacuum(company)

        if company is None:
            company = self.env.company
        if not self.env["res.company"]._check_is_l10n_ro_record(company.id):
            return super(ProductProduct, self)._run_fifo_vacuum(company)

        self.ensure_one()
        svls_to_vacuum = (
            self.env["stock.valuation.layer"]
            .sudo()
            .search(
                [
                    ("product_id", "=", self.id),
                    ("remaining_qty", "<", 0),
                    ("stock_move_id", "!=", False),
                    ("company_id", "=", company.id),
                ],
                order="create_date, id",
            )
        )

        if not svls_to_vacuum:
            return

        as_svls = []

        domain = [
            ("company_id", "=", company.id),
            ("product_id", "=", self.id),
            ("remaining_qty", ">", 0),
            ("create_date", ">=", svls_to_vacuum[0].create_date),
        ]
        all_candidates = self.env["stock.valuation.layer"].sudo().search(domain)
        get_param = self.env["ir.config_parameter"].sudo().get_param
        simple_valuation = get_param("l10n_ro_stock_account.simple_valuation", "False")
        simple_valuation = safe_eval(simple_valuation)
        for location in svls_to_vacuum.mapped("l10n_ro_location_id"):
            svl_loc_to_vaccum = svls_to_vacuum.filtered(
                lambda r: r.l10n_ro_location_id == location
            )
            loc_candidates = all_candidates.filtered(
                lambda r: r.l10n_ro_location_dest_id == location
            )
            if not loc_candidates:
                parent_locations = self.env["stock.location"].search(
                    [("parent_path", "=like", location.parent_path + "%")]
                )
                loc_candidates = all_candidates.filtered(
                    lambda r: r.l10n_ro_location_dest_id in parent_locations
                )
            for svl_to_vacuum in svl_loc_to_vaccum:
                # We don't use search to avoid executing _flush_search and
                # to decrease interaction with DB
                candidates = loc_candidates.filtered(lambda r: r.id > svl_to_vacuum.id)
                if not candidates:
                    break
                qty_to_take_on_candidates = abs(svl_to_vacuum.remaining_qty)
                qty_taken_on_candidates = 0
                tmp_value = 0
                track_svl = []
                for candidate in candidates:
                    qty_taken_on_candidate = min(
                        candidate.remaining_qty, qty_to_take_on_candidates
                    )
                    qty_taken_on_candidates += qty_taken_on_candidate

                    candidate_unit_cost = (
                        candidate.remaining_value / candidate.remaining_qty
                    )
                    value_taken_on_candidate = (
                        qty_taken_on_candidate * candidate_unit_cost
                    )
                    value_taken_on_candidate = candidate.currency_id.round(
                        value_taken_on_candidate
                    )
                    new_remaining_value = (
                        candidate.remaining_value - value_taken_on_candidate
                    )

                    candidate_vals = {
                        "remaining_qty": candidate.remaining_qty
                        - qty_taken_on_candidate,
                        "remaining_value": new_remaining_value,
                    }
                    candidate.write(candidate_vals)
                    track_svl.extend(
                        [
                            (
                                candidate.id,
                                qty_taken_on_candidate,
                                value_taken_on_candidate,
                            )
                        ]
                    )
                    if not (candidate.remaining_qty > 0):
                        all_candidates -= candidate
                        loc_candidates -= candidate

                    qty_to_take_on_candidates -= qty_taken_on_candidate
                    tmp_value += value_taken_on_candidate
                    if float_is_zero(
                        qty_to_take_on_candidates,
                        precision_rounding=self.uom_id.rounding,
                    ):
                        break

                # Get the estimated value we will correct.
                remaining_value_before_vacuum = (
                    svl_to_vacuum.unit_cost * qty_taken_on_candidates
                )
                new_remaining_qty = (
                    svl_to_vacuum.remaining_qty + qty_taken_on_candidates
                )
                corrected_value = remaining_value_before_vacuum - tmp_value
                svl_to_vacuum.write(
                    {
                        "remaining_qty": new_remaining_qty,
                        "remaining_value": new_remaining_qty * svl_to_vacuum.unit_cost,
                    }
                )
                new_remaining_value = svl_to_vacuum.remaining_value + corrected_value
                # svl_to_vacuum._l10n_ro_post_process({"l10n_ro_tracking": track_svl})
                svl_to_vacuum._l10n_ro_create_tracking(track_svl)

                # Don't create a layer or an accounting entry if the corrected value is zero.
                if svl_to_vacuum.currency_id.is_zero(corrected_value):
                    continue

                corrected_value = svl_to_vacuum.currency_id.round(corrected_value)
                move = svl_to_vacuum.stock_move_id
                move_line = svl_to_vacuum.l10n_ro_stock_move_line_id
                if not simple_valuation:
                    vals = {
                        "product_id": self.id,
                        "value": corrected_value,
                        "unit_cost": 0,
                        "quantity": 0,
                        "remaining_qty": 0,
                        "stock_move_id": move.id,
                        "l10n_ro_stock_move_line_id": move_line.id,
                        "company_id": move.company_id.id,
                        "description": "Revaluation of %s (negative inventory)"
                        % move.picking_id.name
                        or move.name,
                        "stock_valuation_layer_id": svl_to_vacuum.id,
                    }
                    vacuum_svl = self.env["stock.valuation.layer"].sudo().create(vals)
                else:
                    vacuum_svl = self.env["stock.valuation.layer"]

                # Create the account move.
                if self.valuation != "real_time":
                    continue
                as_svls.append((vacuum_svl, svl_to_vacuum))

        # If some negative stock were fixed, we need to recompute the standard price.
        product = self.with_company(company.id)
        if product.cost_method == "average" and not float_is_zero(
            product.quantity_svl, precision_rounding=self.uom_id.rounding
        ):
            product.sudo().with_context(disable_auto_svl=True).write(
                {"standard_price": product.value_svl / product.quantity_svl}
            )

        self.env["stock.valuation.layer"].browse(
            x[0].id for x in as_svls
        )._validate_accounting_entries()

        for vacuum_svl, svl_to_vacuum in as_svls:
            self._create_fifo_vacuum_anglo_saxon_expense_entry(
                vacuum_svl, svl_to_vacuum
            )

    @api.model
    def _svl_empty_stock(
        self, description, product_category=None, product_template=None
    ):
        company = (
            self.env["res.company"].browse(self._context.get("force_company"))
            or self.env.company
        )
        if not company.l10n_ro_accounting:
            return super()._svl_empty_stock(
                description,
                product_category=product_category,
                product_template=product_template,
            )

        impacted_product_ids = []
        impacted_products = self.env["product.product"]
        products_orig_quantity_svl = {}

        # get the impacted products
        domain = [("type", "=", "product")]
        if product_category is not None:
            domain += [("categ_id", "=", product_category.id)]
        elif product_template is not None:
            domain += [("product_tmpl_id", "=", product_template.id)]
        else:
            raise ValueError()
        products = self.env["product.product"].search_read(domain, ["quantity_svl"])
        for product in products:
            impacted_product_ids.append(product["id"])
            products_orig_quantity_svl[product["id"]] = product["quantity_svl"]
        impacted_products |= self.env["product.product"].browse(impacted_product_ids)

        # empty out the stock for the impacted products
        empty_stock_svl_list = []
        for product in impacted_products:
            # FIXME sle: why not use products_orig_quantity_svl here?
            if float_is_zero(
                product.quantity_svl, precision_rounding=product.uom_id.rounding
            ):
                # FIXME: create an empty layer to track the change?
                continue
            if (
                float_compare(
                    product.quantity_svl, 0, precision_rounding=product.uom_id.rounding
                )
                > 0
            ):
                svsl_vals = product._prepare_out_svl_vals(
                    product.quantity_svl, self.env.company
                )
            else:
                svsl_vals = [
                    product._prepare_in_svl_vals(
                        abs(product.quantity_svl),
                        product.value_svl / product.quantity_svl,
                    )
                ]
            for vals in svsl_vals:
                if "l10n_ro_tracking" in vals:
                    vals.pop("l10n_ro_tracking")
                vals["description"] = description + vals.pop("rounding_adjustment", "")
                vals["company_id"] = self.env.company.id
            empty_stock_svl_list.extend(svsl_vals)
        return empty_stock_svl_list, products_orig_quantity_svl, impacted_products

    def _svl_replenish_stock(self, description, products_orig_quantity_svl):
        refill_stock_svl_list = []
        l10n_ro_records = self.filtered("is_l10n_ro_record")
        if self - l10n_ro_records:
            refill_stock_svl_list = super(
                ProductProduct, self - l10n_ro_records
            )._svl_replenish_stock(description, products_orig_quantity_svl)
        if l10n_ro_records:
            for product in self:
                quantity_svl = products_orig_quantity_svl[product.id]
                if quantity_svl:
                    if (
                        float_compare(
                            quantity_svl, 0, precision_rounding=product.uom_id.rounding
                        )
                        > 0
                    ):
                        svl_vals = [
                            product._prepare_in_svl_vals(
                                quantity_svl, product.standard_price
                            )
                        ]
                    else:
                        svl_vals = product._prepare_out_svl_vals(
                            abs(quantity_svl), self.env.company
                        )

                    for vals in svl_vals:
                        vals["description"] = description
                        vals["company_id"] = self.env.company.id
                    refill_stock_svl_list.extend(svl_vals)
        return refill_stock_svl_list
