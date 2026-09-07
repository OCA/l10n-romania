# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class RetailOpeningBalance(models.TransientModel):
    """Give the markup ledger a starting position for stock already on the shelf.

    A shop that was trading before this module was installed has goods the
    ledger knows nothing about: the quants carry them, 371 holds their cost,
    and 378 and 4428 hold nothing. Until that is settled the shop is carrying
    its stock at cost rather than at shelf price, and the report says so.

    This wizard measures the gap for each (warehouse, product) - what the
    quants hold against what the ledger has recorded - values it at the current
    shelf price, and posts the difference to 378 and 4428 so 371 comes up to
    the price on the label. It is a one-off: run again afterwards and it finds
    nothing to do.
    """

    _name = "l10n.ro.retail.opening.balance"
    _description = "Retail Markup Opening Balance"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    date = fields.Date(
        required=True,
        default=fields.Date.context_today,
        help="Date of the entry, and of the ledger rows it produces.",
    )
    journal_id = fields.Many2one(
        "account.journal",
        compute="_compute_journal_id",
        store=True,
        readonly=False,
        domain="[('company_id', '=', company_id)]",
    )
    warehouse_ids = fields.Many2many(
        "stock.warehouse",
        string="Shops",
        domain="[('l10n_ro_retail', '=', True), ('company_id', '=', company_id)]",
        help="Leave empty for every retail warehouse of the company.",
    )
    line_ids = fields.One2many(
        "l10n.ro.retail.opening.balance.line", "wizard_id", string="Lines"
    )
    has_shortfall = fields.Boolean(compute="_compute_has_shortfall")

    @api.depends("company_id")
    def _compute_journal_id(self):
        for wizard in self:
            wizard.journal_id = wizard.company_id.account_stock_journal_id

    @api.depends("line_ids.below_cost")
    def _compute_has_shortfall(self):
        for wizard in self:
            wizard.has_shortfall = any(wizard.line_ids.mapped("below_cost"))

    # ------------------------------------------------------------------
    def _l10n_ro_warehouses(self):
        self.ensure_one()
        if self.warehouse_ids:
            return self.warehouse_ids
        return self.env["stock.warehouse"].search(
            [
                ("l10n_ro_retail", "=", True),
                ("company_id", "=", self.company_id.id),
            ]
        )

    def _l10n_ro_gaps(self):
        """Return the ``(warehouse, product)`` pairs the ledger has not caught
        up with, as ``{(warehouse, product): (qty_gap, cost_gap)}``.

        The quants are the authority on what is on the shelf and what it cost;
        the ledger is the record of what has been recognised. Anything the
        first holds and the second does not is what this wizard is for.
        """
        self.ensure_one()
        warehouses = self._l10n_ro_warehouses()
        if not warehouses:
            return {}
        quants = (
            self.env["stock.quant"]
            .sudo()
            .search(
                [
                    ("company_id", "=", self.company_id.id),
                    ("location_id.warehouse_id", "in", warehouses.ids),
                    ("location_id.l10n_ro_retail", "=", True),
                ]
            )
        )
        on_hand = {}
        for quant in quants:
            key = (quant.location_id.warehouse_id, quant.product_id)
            qty, value = on_hand.get(key, (0.0, 0.0))
            on_hand[key] = (qty + quant.quantity, value + quant.value)

        recorded = {}
        groups = (
            self.env["l10n.ro.retail.markup.line"]
            .sudo()
            ._read_group(
                [
                    ("company_id", "=", self.company_id.id),
                    ("warehouse_id", "in", warehouses.ids),
                ],
                groupby=["warehouse_id", "product_id"],
                aggregates=["quantity:sum", "cost:sum"],
            )
        )
        for warehouse, product, qty, cost in groups:
            recorded[(warehouse, product)] = (qty or 0.0, cost or 0.0)

        gaps = {}
        for key in set(on_hand) | set(recorded):
            warehouse, product = key
            qty_hand, cost_hand = on_hand.get(key, (0.0, 0.0))
            qty_done, cost_done = recorded.get(key, (0.0, 0.0))
            qty_gap = qty_hand - qty_done
            cost_gap = cost_hand - cost_done
            rounding = product.uom_id.rounding
            currency_rounding = self.company_id.currency_id.rounding
            if float_is_zero(qty_gap, precision_rounding=rounding) and float_is_zero(
                cost_gap, precision_rounding=currency_rounding
            ):
                continue
            gaps[key] = (qty_gap, cost_gap)
        return gaps

    def action_refresh(self):
        """Measure the gap and show what would be posted."""
        self.ensure_one()
        self.line_ids.unlink()
        currency = self.company_id.currency_id
        vals_list = []
        for (warehouse, product), (qty_gap, cost_gap) in sorted(
            self._l10n_ro_gaps().items(),
            key=lambda item: (item[0][0].id, item[0][1].id),
        ):
            prices = product._l10n_ro_get_retail_prices(
                warehouse=warehouse, company=self.company_id
            )
            retail_no_vat = prices["price_without_vat"] * qty_gap
            vat = currency.round(prices["vat"] * qty_gap)
            markup = currency.round(retail_no_vat - cost_gap)
            vals_list.append(
                {
                    "warehouse_id": warehouse.id,
                    "product_id": product.id,
                    "quantity": qty_gap,
                    "cost": currency.round(cost_gap),
                    "price_unit": prices["price_with_vat"],
                    "markup": markup,
                    "vat": vat,
                    "below_cost": float_compare(
                        markup, 0.0, precision_rounding=currency.rounding
                    )
                    < 0
                    and not warehouse.l10n_ro_retail_allow_negative_markup,
                }
            )
        if vals_list:
            self.line_ids = [Command.create(vals) for vals in vals_list]
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_post(self):
        """Book the opening balance and record it in the ledger."""
        self.ensure_one()
        if not self.journal_id:
            raise UserError(
                self.env._(
                    "No journal to post the opening balance on. Set the stock "
                    "journal on the company, or pick one here."
                )
            )
        if not self.line_ids:
            raise UserError(
                self.env._(
                    "Nothing to post: every shop already carries its stock at "
                    "shelf price."
                )
            )
        shortfall = self.line_ids.filtered("below_cost")
        if shortfall:
            raise UserError(
                self.env._(
                    "These products are priced below what they cost, so the "
                    "opening balance would book a negative markup:\n%(products)s\n\n"
                    "Raise their shelf price, or tick 'Allow Selling Below "
                    "Cost' on the warehouse if the shop means to sell them "
                    "that way.",
                    products="\n".join(
                        f"- {line.product_id.display_name} "
                        f"({line.warehouse_id.display_name})"
                        for line in shortfall
                    ),
                )
            )
        currency = self.company_id.currency_id
        aml_vals = []
        ledger_vals = []
        for line in self.line_ids:
            location = line.warehouse_id.lot_stock_id
            product = line.product_id
            stock_account = location._l10n_ro_get_stock_account(product=product)
            markup_account = location._l10n_ro_get_markup_account(product=product)
            vat_account = location._l10n_ro_get_deferred_vat_account(product=product)
            if not (stock_account and markup_account and vat_account):
                raise UserError(
                    self.env._(
                        "Missing stock valuation (371), markup (378) or "
                        "deferred VAT (4428) account for %(product)s in "
                        "%(warehouse)s.",
                        product=product.display_name,
                        warehouse=line.warehouse_id.display_name,
                    )
                )
            for amount, account in (
                (line.markup, markup_account),
                (line.vat, vat_account),
            ):
                if float_is_zero(amount, precision_rounding=currency.rounding):
                    continue
                aml_vals += line._aml_pair(stock_account, account, amount)
            ledger_vals.append(
                {
                    "company_id": self.company_id.id,
                    "date": self.date,
                    "product_id": product.id,
                    "location_id": location.id,
                    "warehouse_id": line.warehouse_id.id,
                    "quantity": line.quantity,
                    # The cost is already on 371 - it came in with the goods -
                    # so it is recorded, not posted. Only the markup and the
                    # deferred VAT are new entries.
                    "cost": line.cost,
                    "markup": line.markup,
                    "vat": line.vat,
                    "origin_type": "opening",
                    "reference": self.env._("Retail opening balance"),
                }
            )
        move = self.env["account.move"]
        if aml_vals:
            move = self.env["account.move"].create(
                {
                    "journal_id": self.journal_id.id,
                    "date": self.date,
                    "ref": self.env._("Retail markup opening balance"),
                    "line_ids": [Command.create(vals) for vals in aml_vals],
                }
            )
            move._post()
        for vals in ledger_vals:
            vals["account_move_id"] = move.id or False
        self.env["l10n.ro.retail.markup.line"].sudo().create(ledger_vals)
        if not move:
            return {"type": "ir.actions.act_window_close"}
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
        }


class RetailOpeningBalanceLine(models.TransientModel):
    _name = "l10n.ro.retail.opening.balance.line"
    _description = "Retail Markup Opening Balance Line"

    wizard_id = fields.Many2one(
        "l10n.ro.retail.opening.balance", required=True, ondelete="cascade"
    )
    company_id = fields.Many2one(related="wizard_id.company_id")
    currency_id = fields.Many2one(related="company_id.currency_id")
    warehouse_id = fields.Many2one("stock.warehouse", required=True)
    product_id = fields.Many2one("product.product", required=True)
    quantity = fields.Float(
        digits="Product Unit of Measure",
        help="Quantity on hand that the ledger has no record of.",
    )
    cost = fields.Monetary(
        help="What that quantity cost, as the quants value it. It is already "
        "on 371, so it is recorded rather than posted."
    )
    price_unit = fields.Monetary(string="Shelf Price / Unit")
    markup = fields.Monetary(string="Markup (378)")
    vat = fields.Monetary(string="Deferred VAT (4428)")
    below_cost = fields.Boolean(
        string="Priced Below Cost",
        help="The shelf price does not cover the cost, so the opening balance "
        "would book a negative markup.",
    )

    def _aml_pair(self, stock_account, other_account, amount):
        """``Dr 371 / Cr 378`` (or 4428), sides swapped on a negative."""
        self.ensure_one()
        currency = self.company_id.currency_id
        debit_account = stock_account if amount > 0 else other_account
        credit_account = other_account if amount > 0 else stock_account
        value = currency.round(abs(amount))
        base = {
            "name": self.env._(
                "Retail opening balance %(product)s",
                product=self.product_id.display_name,
            ),
            "product_id": self.product_id.id,
            "quantity": self.quantity,
        }
        return [
            dict(base, account_id=debit_account.id, debit=value, credit=0.0),
            dict(base, account_id=credit_account.id, debit=0.0, credit=value),
        ]
