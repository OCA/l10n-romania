# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from datetime import datetime

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Date

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "l10n.ro.mixin"]

    l10n_ro_extra_account_move_ids = fields.One2many(
        "account.move",
        "l10n_ro_extra_stock_move_id",
        string="Extra Account Moves",
        readonly=True,
        copy=False,
    )
    l10n_ro_move_type = fields.Selection(
        [
            ("reception", "Reception"),
            ("reception_return", "Reception Return"),
            ("reception_notice", "Reception Notice"),
            ("reception_notice_return", "Reception Notice Return"),
            ("reception_in_progress", "Reception In Progress"),
            ("reception_in_progress_return", "Reception In Progress Return"),
            ("delivery", "Delivery"),
            ("delivery_return", "Delivery Return"),
            ("delivery_notice", "Delivery Notice"),
            ("delivery_notice_return", "Delivery Notice Return"),
            ("plus_inventory", "Plus Inventory"),
            ("minus_inventory", "Minus Inventory"),
            ("consumption", "Consumption"),
            ("consumption_return", "Consumption Return"),
            ("usage_giving", "Usage Giving"),
            ("usage_giving_return", "Usage Giving Return"),
            ("production", "Production"),
            ("production_return", "Production Return"),
            ("internal_transfer", "Internal Transfer"),
            ("internal_transit_out", "Internal Transit Out"),
            ("internal_transit_in", "Internal Transit In"),
            ("dropshipped", "Dropshipped"),
            ("dropshipped_return", "Dropshipped Return"),
        ],
        compute="_compute_l10n_ro_move_type",
        store=True,
        string="Romanian Move Type",
        help="Specify the type of stock move for Romanian localization.",
    )

    @api.depends(
        "is_in",
        "is_out",
        "state",
        "location_id",
        "location_dest_id",
        "picking_id.l10n_ro_notice",
        "picking_id.l10n_ro_reception_in_progress",
    )
    def _compute_l10n_ro_move_type(self):
        for move in self:
            move.l10n_ro_move_type = move._get_l10n_ro_move_type()

    def _get_l10n_ro_move_type(self):
        self.ensure_one()
        if not self.is_l10n_ro_record:
            return False
        if self.is_in:
            if self.picking_id.l10n_ro_reception_in_progress:
                return "reception_in_progress"
            if self.picking_id.l10n_ro_notice:
                if self.location_id.usage == "supplier":
                    return "reception_notice"
                if self.location_id.usage == "customer":
                    return "delivery_notice_return"
            if self.location_id.usage == "supplier":
                return "reception"
            if self.location_id.usage == "customer":
                return "delivery_return"
            if self.location_id.usage == "inventory":
                return "plus_inventory"
            if self.location_id.usage in "consume":
                return "consumption_return"
            if self.location_id.usage == "usage_giving":
                return "usage_giving_return"
            if self.location_id.usage == "production" and self.origin_returned_move_id:
                return "consumption_return"
            if self.location_id.usage == "production":
                return "production"
            if self.location_id.usage == "transit":
                return "internal_transit_in"
        if self.is_out:
            if self.picking_id.l10n_ro_reception_in_progress:
                return "reception_in_progress_return"
            if self.picking_id.l10n_ro_notice:
                if self.location_dest_id.usage == "supplier":
                    return "reception_notice_return"
                if self.location_dest_id.usage == "customer":
                    return "delivery_notice"
            if self.location_dest_id.usage == "supplier":
                return "reception_return"
            if self.location_dest_id.usage == "customer":
                return "delivery"
            if self.location_dest_id.usage == "inventory":
                return "minus_inventory"
            if self.location_dest_id.usage == "consume":
                return "consumption"
            if self.location_dest_id.usage == "usage_giving":
                return "usage_giving"
            if (
                self.location_dest_id.usage == "production"
                and self.origin_returned_move_id
            ):
                return "production_return"
            if self.location_dest_id.usage == "production":
                return "consumption"
            if self.location_dest_id.usage == "transit":
                return "internal_transit_out"
        if (
            self.location_id.usage == "internal"
            and self.location_dest_id.usage == "internal"
        ):
            # _logger.warning(
            #     self.env._(
            #         "All internal moves should be done through transit location."
            #     )
            # )
            return "internal_transfer"
        if self._is_dropshipped():
            return "dropshipped"
        if self._is_dropshipped_returned():
            return "dropshipped_return"
        return False

    def _get_in_move_lines(self, lot=None):
        res = super()._get_in_move_lines(lot=lot)
        for move_line in self.move_line_ids:
            move = move_line.move_id
            if (
                move.is_l10n_ro_record
                and move_line.location_id.usage in ("internal", "transit")
                and move_line.location_dest_id.usage == "internal"
            ):
                res |= move_line
        return res

    def _get_out_move_lines(self, lot=None):
        res = super()._get_out_move_lines(lot=lot)
        for move_line in self.move_line_ids:
            move = move_line.move_id
            if (
                move.is_l10n_ro_record
                and move_line.location_id.usage == "internal"
                and move_line.location_dest_id.usage in ("internal", "transit")
            ):
                res |= move_line
        return res

    def _set_value(self):
        """Set the value of the move"""
        res = super()._set_value()
        ro_internal_moves = self.filtered(
            lambda m: m.is_l10n_ro_record and m.l10n_ro_move_type == "internal_transfer"
        )
        for move in ro_internal_moves:
            # Since we create double entry throught transfer account
            # we need to set the value to the same as the stock valuation
            move.value = move.sudo()._get_value()
        return res

    def _get_valued_qty(self, lot=None):
        self.ensure_one()
        if self.is_l10n_ro_record and self.l10n_ro_move_type == "internal_transfer":
            return self.product_qty
        return super()._get_valued_qty(lot=lot)

    def _should_create_account_move(self):
        # For Romania we should create account moves for all stock moves
        res = super()._should_create_account_move()
        if self.is_l10n_ro_record:
            res = True
        return res

    def _action_done(self, cancel_backorder=False):
        ro_moves = self.filtered(lambda m: m.is_l10n_ro_record)
        ro_moves._set_locations_from_move_line()
        ro_internal_moves = ro_moves.filtered(
            lambda m: m.l10n_ro_move_type == "internal_transfer"
        )
        ro_internal_moves._set_value()
        res = super()._action_done(cancel_backorder=cancel_backorder)
        for move in ro_moves:
            move._create_account_move_ro_extra()
        return res

    def _set_locations_from_move_line(self):
        # By applying putaway rules, the move location_dest_id
        # will not be the same as the move line location_dest_id.
        # For Romania, we need to have the correct locations on the move
        # to generate correct accounting entries.
        for move in self:
            move_lines_src = move.move_line_ids.mapped("location_id")
            if move_lines_src and len(move_lines_src) == 1:
                move.location_id = move_lines_src
            move_lines_dest = move.move_line_ids.mapped("location_dest_id")
            if move_lines_dest and len(move_lines_dest) == 1:
                move.location_dest_id = move_lines_dest

    def _create_account_move_ro_extra(self):
        """Create account move for specific location or analytic."""
        account_moves = self.env["account.move"]
        for move in self:
            aml_vals_list = []
            if move._should_create_account_move():
                account_list = self._get_l10n_ro_move_type_account_list_extra()
                aml_vals_list = self._get_l10n_ro_move_line_vals_list(
                    account_list, aml_vals_list
                )
                if aml_vals_list:
                    account_move = self.env["account.move"].create(
                        {
                            "l10n_ro_extra_stock_move_id": move.id,
                            "journal_id": self.company_id.account_stock_journal_id.id,
                            "line_ids": [
                                Command.create(aml_vals) for aml_vals in aml_vals_list
                            ],
                            "date": self.env.context.get("force_period_date")
                            or fields.Date.context_today(self),
                        }
                    )
                    account_move._post()
                    account_moves |= account_move
        return account_moves

    @api.model
    def _get_l10n_ro_move_type_account_list(self):
        # Return a list of tuples (from_account_key, to_account_key, price_type)
        # defining which accounts to use for the stock valuation entry
        # depending on the move type.
        # price_type is either 'value' or 'sale_price'
        vals = {
            "reception": [],
            "reception_return": [],
            "reception_notice": [
                ("stock_valuation", "l10n_ro_picking_payable", "value", 1)
            ],
            "reception_notice_return": [
                ("stock_valuation", "l10n_ro_picking_payable", "value", -1)
            ],
            "reception_in_progress": [
                ("stock_valuation", "l10n_ro_reception_in_progress", "value", 1)
            ],
            "reception_in_progress_return": [
                ("stock_valuation", "l10n_ro_reception_in_progress", "value", -1)
            ],
            "delivery": [("expense", "stock_valuation", "value", 1)],
            "delivery_return": [("expense", "stock_valuation", "value", -1)],
            "delivery_notice": [("expense", "stock_valuation", "value", 1)],
            "delivery_notice_return": [("expense", "stock_valuation", "value", -1)],
            "plus_inventory": [("expense", "stock_valuation", "value", -1)],
            "minus_inventory": [("expense", "stock_valuation", "value", 1)],
            "consumption": [("expense", "stock_valuation", "value", 1)],
            "consumption_return": [("expense", "stock_valuation", "value", -1)],
            "usage_giving": [("expense", "stock_valuation", "value", 1)],
            "usage_giving_return": [("expense", "stock_valuation", "value", -1)],
            "production": [("stock_valuation", "expense", "value", 1)],
            "production_return": [("stock_valuation", "expense", "value", -1)],
            "internal_transfer": [
                ("l10n_ro_transfer", "stock_valuation", "value", 1),
                ("expense", "l10n_ro_transfer", "value", 1),
            ],
            "internal_transit_out": [
                ("l10n_ro_transfer", "stock_valuation", "value", 1)
            ],
            "internal_transit_in": [
                ("stock_valuation", "l10n_ro_transfer", "value", 1)
            ],
            "dropshipped": [],
            "dropshipped_return": [],
        }
        return vals.get(self.l10n_ro_move_type, [])

    @api.model
    def _get_l10n_ro_move_type_account_list_extra(self):
        vals = {
            "delivery_notice": [
                ("l10n_ro_picking_receivable", "income", "sale_price", 1)
            ],
            "delivery_notice_return": [
                ("l10n_ro_picking_receivable", "income", "sale_price", -1)
            ],
            "usage_giving": [
                ("l10n_ro_usage_giving", "l10n_ro_usage_giving", "value", 1)
            ],
            "usage_giving_return": [
                ("l10n_ro_usage_giving", "l10n_ro_usage_giving", "value", -1)
            ],
        }
        return vals.get(self.l10n_ro_move_type, [])

    def _get_l10n_ro_value(self, price_type):
        self.ensure_one()
        if price_type == "value":
            return self.value
        if price_type == "sale_price":
            if hasattr(self, "sale_line_id") and self.sale_line_id is not None:
                sale_value = self.company_id.currency_id._convert(
                    self.sale_line_id.price_unit * self.quantity,
                    self.env.company.currency_id,
                    self.company_id,
                    self.date,
                )
                return sale_value
            else:
                raise UserError(
                    self.env._(
                        "Stock move %(move)s has no linked "
                        "sale line for sale price computation",
                        move=self.display_name,
                    )
                )
        raise UserError(self.env._("Unknown price type %(type)s", type=price_type))

    def _get_account_move_line_vals(self):
        res = super()._get_account_move_line_vals()
        if self.is_l10n_ro_record:
            res = []
            if not self.l10n_ro_move_type:
                raise UserError(
                    self.env._(
                        "Romanian Stock Move Type not set on stock move %(move)s",
                        move=self.display_name,
                    )
                )
            account_list = self._get_l10n_ro_move_type_account_list()
            res = self._get_l10n_ro_move_line_vals_list(account_list, res)
        return res

    def _get_l10n_ro_move_line_vals_list(
        self, account_list=None, res=None, forced_value=None
    ):
        acc_obj = self.env["account.account"]
        if not account_list:
            return res
        accounts = self.product_id.product_tmpl_id.with_context(
            l10n_ro_stock_move=self
        ).get_product_accounts()
        if not accounts.get("stock_valuation"):
            raise UserError(
                self.env._(
                    "No stock valuation account found for product %(product)s. "
                    "Make sure you have a stock valuation account defined "
                    "on the product or its category, and that the product "
                    "is storable.",
                    product=self.product_id.display_name,
                )
            )
        if self.l10n_ro_move_type == "internal_transfer" and accounts.get(
            "expense"
        ) == accounts.get("stock_valuation"):
            return res
        for from_key, to_key, price_type, sign in account_list:
            debit_acc = accounts.get(from_key, acc_obj)
            credit_acc = accounts.get(to_key, acc_obj)
            if not forced_value:
                forced_value = self._get_l10n_ro_value(price_type)
            value = sign * forced_value
            if not debit_acc:
                raise UserError(
                    self.env._(
                        "Missing debit account when generating account move for "
                        "stock move line %(move)s",
                        move=self.display_name,
                    )
                )
            if not credit_acc:
                raise UserError(
                    self.env._(
                        "Missing credit account when generating account move for "
                        "stock move line %(move)s",
                        move=self.display_name,
                    )
                )
            if not value:
                continue
            if debit_acc == credit_acc and debit_acc != accounts.get(
                "l10n_ro_usage_giving", False
            ):
                continue
            res += [
                {
                    "account_id": debit_acc.id,
                    "name": self.reference,
                    "product_id": self.product_id.id,
                    "quantity": self.product_qty,
                    "debit": value,
                    "credit": 0,
                    "is_storno": value < 0,
                },
                {
                    "account_id": credit_acc.id,
                    "name": self.reference,
                    "product_id": self.product_id.id,
                    "quantity": self.product_qty,
                    "debit": 0,
                    "credit": value,
                    "is_storno": value < 0,
                },
            ]
        if self.l10n_ro_move_type in (
            "consumption",
            "usage_giving",
            "consumption_return",
            "usage_giving_return",
        ):
            account = self.env["account.account"]
            if self.l10n_ro_move_type in ("consumption", "usage_giving"):
                account = credit_acc
            else:
                account = debit_acc
            if account and account.l10n_ro_stock_consume_account_id:
                res += [
                    {
                        "account_id": account.l10n_ro_stock_consume_account_id.id,
                        "name": self.reference,
                        "debit": value,
                        "credit": 0,
                        "product_id": self.product_id.id,
                        "is_storno": value < 0,
                    },
                    {
                        "account_id": account.l10n_ro_stock_consume_account_id.id,
                        "name": self.reference,
                        "debit": 0,
                        "credit": value,
                        "product_id": self.product_id.id,
                        "is_storno": value < 0,
                    },
                ]
        return res

    def _get_value_from_account_move(self, quantity, at_date=None):
        # Override since there are some errors from commit
        # https://github.com/odoo/odoo/commit/47345b1fc8b805e232a4287cc6d5c54b2f5886cb
        valuation_data = dict(quantity=0, value=0, description=False)
        if not self.purchase_line_id:
            return valuation_data

        if not self.company_id.l10n_ro_accounting:
            return super()._get_value_from_account_move(quantity, at_date=at_date)
        if isinstance(at_date, datetime):
            # Since aml.date are Date, we don't need the extra precision here.
            at_date = Date.to_date(at_date)

        aml_quantity = 0
        value = 0
        aml_ids = set()
        for aml in self.purchase_line_id.invoice_lines:
            if at_date and aml.date > at_date:
                continue
            if aml.move_id.state != "posted":
                continue
            aml_ids.add(aml.id)
            if aml.move_type == "in_invoice":
                aml_quantity += aml.product_uom_id._compute_quantity(
                    aml.quantity, self.product_id.uom_id
                )  # noqa
                value += aml.currency_id._convert(
                    aml.price_subtotal, self.company_id.currency_id, date=aml.date
                )  # noqa
            elif aml.move_type == "in_refund":
                aml_quantity -= aml.product_uom_id._compute_quantity(
                    aml.quantity, self.product_id.uom_id
                )  # noqa
                value -= aml.currency_id._convert(
                    aml.price_subtotal, self.company_id.currency_id, date=aml.date
                )  # noqa

        if aml_quantity <= 0:
            return valuation_data

        # other_candidates_qty = 0
        # for move in self.purchase_line_id.move_ids:
        #     if move.product_id != self.product_id:
        #         continue
        #     if move.date > self.date or (move.date == self.date and move.id > self.id): # noqa
        #         continue
        #     if move.is_in or move.is_dropship:
        #         other_candidates_qty += move._get_valued_qty() # noqa
        #     elif move.is_out:
        #         other_candidates_qty -= -move._get_valued_qty() # noqa

        # if self.product_uom.compare(aml_quantity, other_candidates_qty) <= 0: # noqa
        #     return valuation_data

        # # Remove quantity from prior moves.
        # value = value * ((aml_quantity - other_candidates_qty) / aml_quantity) # noqa
        # aml_quantity = aml_quantity - other_candidates_qty

        if quantity >= aml_quantity:
            valuation_data["quantity"] = aml_quantity
            valuation_data["value"] = value
        else:
            valuation_data["quantity"] = quantity
            valuation_data["value"] = quantity * value / aml_quantity  # noqa
        account_moves = self.env["account.move.line"].browse(aml_ids).move_id  # noqa
        valuation_data["description"] = self.env._(
            "%(value)s for %(quantity)s %(unit)s from %(bills)s",  # noqa
            value=self.company_currency_id.format(value),
            quantity=aml_quantity,
            unit=self.product_id.uom_id.name,  # noqa
            bills=account_moves.mapped("display_name"),
        )
        return valuation_data
