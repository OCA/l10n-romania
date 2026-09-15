# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.sql import column_exists, create_column

_logger = logging.getLogger(__name__)

# Kept as a module level constant so that other modules can reuse it; up to 18.0
# the same list lived on stock.valuation.layer as VALUED_TYPE, and the storage
# sheet report imported it from there.
MOVE_TYPE = [
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
]


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "l10n.ro.mixin"]

    l10n_ro_extra_account_move_ids = fields.One2many(
        "account.move",
        "l10n_ro_extra_stock_move_id",
        string="Romania - Extra Account Moves",
        readonly=True,
        copy=False,
    )
    l10n_ro_move_type = fields.Selection(
        MOVE_TYPE,
        compute="_compute_l10n_ro_move_type",
        store=True,
        string="Romanian - Move Type",
        help="Specify the type of stock move for Romanian localization.",
    )

    l10n_ro_account_id = fields.Many2one(
        "account.account",
        compute="_compute_account",
        store=True,
        string="Romania - Valuation Account",
    )
    l10n_ro_transfer_account_id = fields.Many2one(
        "account.account",
        compute="_compute_account",
        store=True,
        string="Romania - Transfer Valuation Account",
    )

    @api.depends("product_id", "account_move_id")
    def _compute_account(self):
        for move in self.filtered(lambda m: m.is_l10n_ro_record):
            account = self.env["account.account"]
            move = move.with_company(move.company_id)

            loc_dest = move.location_dest_id
            loc_src = move.location_id
            account = (
                move.product_id.l10n_ro_property_stock_valuation_account_id
                or move.product_id.categ_id.property_stock_valuation_account_id
            )
            transfer_account = account
            if move.product_id.categ_id.l10n_ro_stock_account_change:
                if (
                    move.value > 0
                    and loc_dest.l10n_ro_property_stock_valuation_account_id
                ):
                    account = loc_dest.l10n_ro_property_stock_valuation_account_id
                if (
                    move.value < 0
                    and loc_src.l10n_ro_property_stock_valuation_account_id
                ):
                    account = loc_src.l10n_ro_property_stock_valuation_account_id
                if loc_src.usage == "internal" and loc_dest.usage == "transit":
                    if loc_dest.l10n_ro_property_stock_valuation_account_id:
                        account = loc_dest.l10n_ro_property_stock_valuation_account_id
                    elif loc_dest.company_id.l10n_ro_property_stock_transfer_account_id:
                        account = loc_src.company_id.l10n_ro_property_stock_transfer_account_id  # noqa: E501
            if move.account_move_id and "internal" not in move.l10n_ro_move_type:
                for account_move in move.account_move_id:
                    for aml in account_move.line_ids.sorted(
                        lambda line: line.account_id.code or ""
                    ):
                        if aml.account_id.code and aml.account_id.code[0] in ["2", "3"]:
                            if round(aml.balance, 2) == round(move.value, 2):
                                account = aml.account_id
                                break
            move.l10n_ro_account_id = account

            if (
                loc_src.usage in ("internal", "transit")
                and loc_dest.usage == "internal"
            ):
                if loc_src.l10n_ro_property_stock_valuation_account_id:
                    transfer_account = (
                        loc_src.l10n_ro_property_stock_valuation_account_id
                    )
                elif (
                    loc_src.usage == "transit"
                    and loc_src.company_id.l10n_ro_property_stock_transfer_account_id
                ):
                    transfer_account = (
                        loc_src.company_id.l10n_ro_property_stock_transfer_account_id
                    )
            elif loc_src.usage == "internal" and loc_dest.usage == "transit":
                if loc_src.l10n_ro_property_stock_valuation_account_id:
                    transfer_account = (
                        loc_src.l10n_ro_property_stock_valuation_account_id
                    )

            move.l10n_ro_transfer_account_id = (
                transfer_account.id
                if transfer_account and transfer_account != account
                else False
            )

    def _auto_init(self):
        if not column_exists(self.env.cr, "stock_move", "l10n_ro_transfer_account_id"):
            if column_exists(
                self.env.cr,
                "stock_location",
                "l10n_ro_property_stock_valuation_account_id",
            ):
                create_column(
                    self.env.cr,
                    "stock_move",
                    "l10n_ro_transfer_account_id",
                    "integer",
                )
                self.env.cr.execute(
                    """
                        UPDATE stock_move sm
                        SET l10n_ro_transfer_account_id =
                            (sl.l10n_ro_property_stock_valuation_account_id->>'sm.company_id')::integer
                        FROM stock_location sl, stock_location sld
                        WHERE sm.location_id = sl.id
                        AND sm.location_dest_id = sld.id
                        AND sl.usage = 'internal'
                        AND sld.usage = 'internal'
                        AND sl.l10n_ro_property_stock_valuation_account_id IS NOT NULL
                    """,
                )  # noqa
        return super()._auto_init()

    @api.depends(
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
        if (
            self.location_id.usage != "internal"
            and self.location_dest_id.usage == "internal"
        ):
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
        if (
            self.location_id.usage == "internal"
            and self.location_dest_id.usage != "internal"
        ):
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

    def _compute_reference(self):
        res = super()._compute_reference()
        ro_moves_without_ref = self.filtered(
            lambda m: m.is_l10n_ro_record and not m.reference
        )
        for move in ro_moves_without_ref:
            move.reference = move.display_name
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

    def _set_value(self, correction_quantity=None):
        """Set the value of the move"""
        # Dropship moves gain nothing from core's own _set_value (they never
        # satisfy its is_in/_is_out branches), but core still adds their
        # product to `products_to_recompute` (keyed on `is_dropship or
        # is_in`) and later recomputes the average cost for it — folding the
        # dropship cost into the SAME moving-average pool as the company's
        # real stock of that product (core's `_run_average_batch` explicitly
        # includes `is_dropship` moves), which retroactively reprices
        # unrelated quants already on hand. Route dropship moves around
        # core's _set_value entirely and value them ourselves below instead.
        ro_dropship_moves = self.filtered(
            lambda m: m.is_l10n_ro_record
            and m.l10n_ro_move_type in ("dropshipped", "dropshipped_return")
        )
        res = super(StockMove, self - ro_dropship_moves)._set_value(
            correction_quantity=correction_quantity
        )
        ro_internal_moves = self.filtered(
            lambda m: m.is_l10n_ro_record and m.l10n_ro_move_type == "internal_transfer"
        )
        for move in ro_internal_moves:
            # Since we create double entry throught transfer account
            # we need to set the value to the same as the stock valuation
            move.value = move.sudo()._get_value()

        for move in ro_dropship_moves.filtered(lambda m: not m.value):
            move.value = move.sudo()._get_value()
        return res

    def _l10n_ro_get_source_account_unit_cost(self):
        """Unit cost the source warehouse account actually holds for the product.

        An internal transfer must move the value the source warehouse owns for
        the goods, not the average taken over every warehouse. The balance is
        rebuilt from the done moves in and out of the locations sharing the
        source valuation account, which is what the storage sheet reports per
        warehouse.

        Returns ``None`` when the cost cannot be established, in which case the
        caller keeps the standard behaviour. This is notably the case when the
        source location has no valuation account of its own: source and
        destination then share the product account and the global cost is
        already the right one.
        """
        self.ensure_one()
        src_account = self.location_id.with_company(
            self.company_id
        ).l10n_ro_property_stock_valuation_account_id
        if not src_account:
            return None
        locations = (
            self.env["stock.location"]
            .sudo()
            .with_company(self.company_id)
            .search(
                [
                    ("usage", "=", "internal"),
                    ("company_id", "in", [False, self.company_id.id]),
                    (
                        "l10n_ro_property_stock_valuation_account_id",
                        "=",
                        src_account.id,
                    ),
                ]
            )
        )
        if not locations:
            return None
        domain = [
            ("product_id", "=", self.product_id.id),
            ("state", "=", "done"),
            ("company_id", "=", self.company_id.id),
            ("id", "!=", self.id),
        ]
        move_obj = self.env["stock.move"].sudo()
        value = quantity = 0.0
        # Moves landing in the warehouse add value, moves leaving it remove
        # value; a move inside the warehouse appears on both sides and cancels
        # out, as it should.
        for sign, location_field in ((1, "location_dest_id"), (-1, "location_id")):
            groups = move_obj._read_group(
                domain + [(location_field, "in", locations.ids)],
                aggregates=["value:sum", "product_qty:sum"],
            )
            # _read_group returns an empty list when nothing matches.
            group_value, group_quantity = groups[0] if groups else (0.0, 0.0)
            value += sign * (group_value or 0.0)
            quantity += sign * (group_quantity or 0.0)
        if quantity <= 0 or self.product_id.uom_id.is_zero(quantity):
            return None
        unit_cost = value / quantity
        if unit_cost <= 0:
            # A warehouse left with a negative balance by earlier
            # mis-valuations gives a negative cost, which is not a cost the
            # goods can be taken out at: the move would be valued negatively,
            # which runs its whole entry backwards - the source warehouse
            # debited instead of credited - so the transfer would deepen the
            # negative balance instead of relieving it. Keep the standard
            # valuation and let the existing imbalance be corrected on its own.
            return None
        return unit_cost

    def _get_value_from_std_price(self, quantity, std_price=False, at_date=None):
        """Value an internal transfer at the cost held by the source warehouse.

        Only the last step of ``_get_value_data`` is replaced, so a value coming
        from a bill, a quotation, a return or a landed cost keeps priority
        exactly as in the standard flow; the override kicks in only where the
        standard flow would fall back to the product's global cost.

        FIFO and lot valued products are left alone: there the cost already
        comes from the layers or from the lot, not from a global average.
        """
        if (
            not std_price
            and not at_date
            and self.is_l10n_ro_record
            and self.l10n_ro_move_type == "internal_transfer"
            and self.product_id.cost_method != "fifo"
            and not self.product_id.lot_valuated
        ):
            unit_cost = self.sudo()._l10n_ro_get_source_account_unit_cost()
            if unit_cost is not None:
                return {
                    "value": unit_cost * quantity,
                    "quantity": quantity,
                    "description": self.env._(
                        "%(quantity)s %(uom)s at the cost of the source warehouse",
                        quantity=quantity,
                        uom=self.product_id.uom_id.name,
                    ),
                }
        return super()._get_value_from_std_price(
            quantity, std_price=std_price, at_date=at_date
        )

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
            "dropshipped": [("expense", "stock_valuation", "value", 1)],
            "dropshipped_return": [("expense", "stock_valuation", "value", -1)],
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

    def _l10n_ro_get_pivot_currency_amount(self, value):
        """Return (currency, amount) for the 408 leg of a reception on notice.

        When the reception comes from a purchase order in a foreign currency,
        the estimated liability is a monetary item and must keep the order
        currency, so the exchange rate difference between reception and invoice
        can be recognised when the invoice arrives (OMFP 1802/2014, function of
        account 408). The stock leg stays in company currency at the reception
        rate, inventory being a non-monetary asset that is not retranslated
        (IAS 21).
        """
        self.ensure_one()
        company_currency = self.company_id.currency_id
        po_line = self.purchase_line_id if "purchase_line_id" in self._fields else False
        if po_line and po_line.currency_id and po_line.currency_id != company_currency:
            qty = self.product_uom._compute_quantity(
                self.quantity, po_line.product_uom_id
            )
            return po_line.currency_id, po_line.price_unit * qty
        return company_currency, value

    def _l10n_ro_pivot_currency_vals(self, account_key, value, leg_sign):
        """Extra values carrying the order currency on the 408 leg of a notice
        reception. Empty for every other account and move type."""
        self.ensure_one()
        if account_key != "l10n_ro_picking_payable":
            return {}
        if not (self.l10n_ro_move_type or "").startswith("reception_notice"):
            return {}
        currency, amount = self._l10n_ro_get_pivot_currency_amount(value)
        if currency == self.company_id.currency_id:
            return {}
        # `value` already carries the storno sign of the entry; mirror it here
        signed = amount if value > 0 else -amount
        return {"currency_id": currency.id, "amount_currency": leg_sign * signed}

    def _get_value_from_bill(self, aml):
        """Keep the reception rate for the quantity already received on notice.

        Inventory is a non-monetary asset and is not retranslated for exchange
        rate movements (IAS 21 / OMFP 1802): the rate delta belongs on 765/665,
        not in the stock value. Only the part invoiced beyond the reception - a
        genuine price difference, whose liability arises at the invoice date -
        is taken at the invoice rate.

        Defined by `purchase_stock`, the only caller, so this override is
        reached exclusively on that path.
        """
        self.ensure_one()
        company_currency = self.company_id.currency_id
        if self.company_id.l10n_ro_accounting:
            rate_diff = aml._l10n_ro_notice_rate_difference()
            if not company_currency.is_zero(rate_diff):
                return company_currency.round(aml.balance + rate_diff)
        return super()._get_value_from_bill(aml)

    def _get_l10n_ro_value(self, price_type):
        self.ensure_one()
        if price_type == "value":
            return self.value
        if price_type == "sale_price":
            if hasattr(self, "sale_line_id") and self.sale_line_id is not None:
                sale_value = self.sale_line_id.currency_id._convert(
                    self.sale_line_id.price_unit * self.quantity,
                    self.company_id.currency_id,
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
            debit_vals = {
                "account_id": debit_acc.id,
                "name": self.reference,
                "product_id": self.product_id.id,
                "quantity": self.product_qty,
                "debit": value,
                "credit": 0,
                "is_storno": value < 0,
            }
            credit_vals = {
                "account_id": credit_acc.id,
                "name": self.reference,
                "product_id": self.product_id.id,
                "quantity": self.product_qty,
                "debit": 0,
                "credit": value,
                "is_storno": value < 0,
            }
            debit_vals.update(self._l10n_ro_pivot_currency_vals(from_key, value, 1))
            credit_vals.update(self._l10n_ro_pivot_currency_vals(to_key, value, -1))
            res += [debit_vals, credit_vals]
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

    # def _get_value_from_account_move(self, quantity, at_date=None):
    #     # Override since there are some errors from commit
    #     # https://github.com/odoo/odoo/commit/47345b1fc8b805e232a4287cc6d5c54b2f5886cb
    #     valuation_data = dict(quantity=0, value=0, description=False)
    #     if not self.purchase_line_id:
    #         return valuation_data

    #     if not self.company_id.l10n_ro_accounting:
    #         return super()._get_value_from_account_move(quantity, at_date=at_date)
    #     if isinstance(at_date, datetime):
    #         # Since aml.date are Date, we don't need the extra precision here.
    #         at_date = Date.to_date(at_date)

    #     aml_quantity = 0
    #     value = 0
    #     aml_ids = set()
    #     for aml in self.purchase_line_id.invoice_lines:
    #         if at_date and aml.date > at_date:
    #             continue
    #         if aml.move_id.state != "posted":
    #             continue
    #         aml_ids.add(aml.id)
    #         if aml.move_type == "in_invoice":
    #             aml_quantity += aml.product_uom_id._compute_quantity(
    #                 aml.quantity, self.product_id.uom_id
    #             )  # noqa
    #             value += aml.currency_id._convert(
    #                 aml.price_subtotal, self.company_id.currency_id, date=aml.date
    #             )  # noqa
    #         elif aml.move_type == "in_refund":
    #             aml_quantity -= aml.product_uom_id._compute_quantity(
    #                 aml.quantity, self.product_id.uom_id
    #             )  # noqa
    #             value -= aml.currency_id._convert(
    #                 aml.price_subtotal, self.company_id.currency_id, date=aml.date
    #             )  # noqa

    #     if aml_quantity <= 0:
    #         return valuation_data

    #     # other_candidates_qty = 0
    #     # for move in self.purchase_line_id.move_ids:
    #     #     if move.product_id != self.product_id:
    #     #         continue
    #     #     if move.date > self.date or (move.date == self.date and move.id > self.id): # noqa
    #     #         continue
    #     #     if move.is_in or move.is_dropship:
    #     #         other_candidates_qty += move._get_valued_qty() # noqa
    #     #     elif move.is_out:
    #     #         other_candidates_qty -= -move._get_valued_qty() # noqa

    #     # if self.product_uom.compare(aml_quantity, other_candidates_qty) <= 0: # noqa
    #     #     return valuation_data

    #     # # Remove quantity from prior moves.
    #     # value = value * ((aml_quantity - other_candidates_qty) / aml_quantity) # noqa
    #     # aml_quantity = aml_quantity - other_candidates_qty

    #     if quantity >= aml_quantity:
    #         valuation_data["quantity"] = aml_quantity
    #         valuation_data["value"] = value
    #     else:
    #         valuation_data["quantity"] = quantity
    #         valuation_data["value"] = quantity * value / aml_quantity  # noqa
    #     account_moves = self.env["account.move.line"].browse(aml_ids).move_id  # noqa
    #     valuation_data["description"] = self.env._(
    #         "%(value)s for %(quantity)s %(unit)s from %(bills)s",  # noqa
    #         value=self.company_currency_id.format(value),
    #         quantity=aml_quantity,
    #         unit=self.product_id.uom_id.name,  # noqa
    #         bills=account_moves.mapped("display_name"),
    #     )
    #     return valuation_data
