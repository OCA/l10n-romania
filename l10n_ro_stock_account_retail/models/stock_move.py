# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class StockMove(models.Model):
    _inherit = "stock.move"

    l10n_ro_retail_markup_line_ids = fields.One2many(
        "l10n.ro.retail.markup.line",
        "move_id",
        string="Retail Markup Ledger",
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Which side(s) of the retail boundary this move crosses
    # ------------------------------------------------------------------
    def _l10n_ro_retail_legs(self):
        """Return a list of ``(direction, location, warehouse)`` legs to book.

        - ``('in', dest_loc, dest_wh)``  goods enter a retail location
        - ``('out', src_loc, src_wh)``   goods leave a retail location

        A move between two retail warehouses in a single step produces both
        legs. Multi-step transfers reach the same result on their own: the
        transit location is not internal, hence not retail, so the first move
        releases the source shop's markup and the second loads the destination
        shop's - each at its own shelf price, which is what the two shops must
        each carry on their 371.

        Moves that stay inside one retail warehouse book nothing: the markup is
        held per warehouse, so moving goods from the shelf to the counter does
        not change it.
        """
        self.ensure_one()
        src_retail = self.location_id.l10n_ro_retail
        dest_retail = self.location_dest_id.l10n_ro_retail
        if not src_retail and not dest_retail:
            return []
        src_wh = self.location_id.warehouse_id
        dest_wh = self.location_dest_id.warehouse_id
        if src_retail and dest_retail:
            if src_wh == dest_wh:
                return []
            return [
                ("out", self.location_id, src_wh),
                ("in", self.location_dest_id, dest_wh),
            ]
        if dest_retail:
            return [("in", self.location_dest_id, dest_wh)]
        return [("out", self.location_id, src_wh)]

    def _l10n_ro_retail_is_valued(self):
        """Whether this move can carry a retail markup at all.

        A service or a consumable has no stock accounts to post to, and a
        company or category on periodic valuation books nothing in real time.
        Posting for either used to raise deep inside the entry builder, on a
        missing account, instead of simply not applying.

        The answer is read from ``product.valuation``, not from the category
        setting. ``property_valuation`` is company dependent and routinely
        empty, in which case Odoo falls back to ``company.inventory_valuation``
        - reading the category alone therefore saw nothing on any database that
        configures valuation at company level, and silently skipped the whole
        retail treatment.
        """
        self.ensure_one()
        product = self.product_id.with_company(self.company_id)
        return bool(
            self.is_l10n_ro_record
            and product.is_storable
            and product.valuation == "real_time"
        )

    # ------------------------------------------------------------------
    # How much markup and VAT each leg moves
    # ------------------------------------------------------------------
    def _l10n_ro_retail_return_amounts(self, direction, qty):
        """Markup and VAT to book for a return, taken from the move being
        returned rather than from today's pricelist.

        A customer return has to put back on 378 and 4428 exactly what the sale
        released, and a return to a vendor has to take off exactly what the
        reception loaded. Valuing a return at the current shelf price leaves a
        residue on both accounts whenever the price moved in between - the very
        thing the ledger exists to prevent.

        Returns ``None`` when there is nothing to prorate, so the caller falls
        back to the normal valuation.
        """
        self.ensure_one()
        origin = self.origin_returned_move_id
        if not origin:
            return None
        # A return reverses the original leg: goods coming back into the shop
        # restore what the outgoing leg released, and the other way round.
        origin_direction = "out" if direction == "in" else "in"
        lines = origin.l10n_ro_retail_markup_line_ids.filtered(
            lambda line, d=origin_direction: (
                (line.quantity < 0) if d == "out" else (line.quantity > 0)
            )
        )
        if not lines:
            return None
        origin_qty = abs(sum(lines.mapped("quantity")))
        if float_is_zero(
            origin_qty, precision_rounding=self.product_id.uom_id.rounding
        ):
            return None
        ratio = min(qty / origin_qty, 1.0)
        markup = abs(sum(lines.mapped("markup"))) * ratio
        vat = abs(sum(lines.mapped("vat"))) * ratio
        return markup, vat

    def _l10n_ro_retail_in_amounts(self, location, warehouse, qty):
        """Markup and VAT to load when ``qty`` enters a retail warehouse."""
        self.ensure_one()
        returned = self._l10n_ro_retail_return_amounts("in", qty)
        if returned is not None:
            return returned
        currency = self.company_id.currency_id
        cost_unit = abs(self.value) / qty if qty else 0.0
        prices = self.product_id._l10n_ro_get_retail_prices(
            warehouse=warehouse, company=self.company_id
        )
        markup_unit = prices["price_without_vat"] - cost_unit
        if (
            float_compare(markup_unit, 0.0, precision_rounding=currency.rounding) < 0
            and not warehouse.l10n_ro_retail_allow_negative_markup
        ):
            minimum = self.product_id._l10n_ro_minimum_retail_price(
                cost_unit, company=self.company_id
            )
            raise UserError(
                self.env._(
                    "The retail price of %(product)s in %(warehouse)s is below "
                    "cost: it would book a negative markup on 378.\n"
                    "Cost per unit: %(cost).2f\n"
                    "Shelf price (PVA, VAT included): %(price).2f\n"
                    "Minimum shelf price: %(minimum).2f\n\n"
                    "Correct the price on the retail pricelist, or tick "
                    "'Allow Selling Below Cost' on the warehouse if the shop "
                    "genuinely sells this below cost.",
                    product=self.product_id.display_name,
                    warehouse=warehouse.display_name,
                    cost=cost_unit,
                    price=prices["price_with_vat"],
                    minimum=minimum,
                )
            )
        return markup_unit * qty, prices["vat"] * qty

    def _l10n_ro_retail_out_amounts(self, location, warehouse, qty, exclude=None):
        """Markup and VAT to release when ``qty`` leaves a retail warehouse.

        Taken from the ledger, never recomputed from the pricelist: the release
        has to match what was loaded. The rate is the balance carried divided by
        the quantity that carries it - the *coeficient de repartizare a
        adaosului comercial* - so the last unit out closes 378 and 4428 to zero
        instead of leaving a residue behind.
        """
        self.ensure_one()
        returned = self._l10n_ro_retail_return_amounts("out", qty)
        if returned is not None:
            return returned
        Ledger = self.env["l10n.ro.retail.markup.line"]
        # Both halves of the rate come from the ledger: the balance carried and
        # the quantity carrying it. Taking the quantity from the quants instead
        # looks equivalent - normally the two agree exactly - but they part
        # company as soon as the ledger has a gap, and then the rate is
        # nonsense. Stock that was already in the shop when this module was
        # installed is the usual gap: the quants know about it, the ledger does
        # not, and dividing a small recorded markup by a large on-hand quantity
        # dribbles out a fraction of a leu per sale and never closes 378.
        #
        # This move's own rows are written after the entry is built, so what
        # the ledger holds here is the position before it.
        qty_before, _cost, markup, vat = Ledger._l10n_ro_balance(
            warehouse, self.product_id, self.company_id
        )
        rounding = self.product_id.uom_id.rounding
        if float_is_zero(
            markup, precision_rounding=self.company_id.currency_id.rounding
        ) and float_is_zero(
            vat, precision_rounding=self.company_id.currency_id.rounding
        ):
            return 0.0, 0.0
        if float_compare(qty_before, qty, precision_rounding=rounding) <= 0:
            # The ledger accounts for no more than what is leaving, so
            # everything it carries goes with it and both accounts close.
            return markup, vat
        ratio = qty / qty_before
        return markup * ratio, vat * ratio

    # ------------------------------------------------------------------
    # Journal entries
    # ------------------------------------------------------------------
    def _l10n_ro_get_retail_aml_vals(self, ledger_vals):
        """Build the markup (378) and deferred VAT (4428) lines for this move,
        appending the matching ledger rows to ``ledger_vals``."""
        self.ensure_one()
        if not self._l10n_ro_retail_is_valued():
            return []
        legs = self._l10n_ro_retail_legs()
        if not legs:
            return []
        qty = self.product_qty
        if float_is_zero(qty, precision_rounding=self.product_id.uom_id.rounding):
            return []
        currency = self.company_id.currency_id
        aml_vals = []
        for direction, location, warehouse in legs:
            stock_account = location._l10n_ro_get_stock_account(product=self.product_id)
            if not stock_account:
                raise UserError(
                    self.env._(
                        "No stock valuation account (371) for product "
                        "%(product)s at location %(location)s. Set it on the "
                        "location, the product or its category before moving "
                        "goods in or out of a retail warehouse.",
                        product=self.product_id.display_name,
                        location=location.display_name,
                    )
                )
            markup_account = location._l10n_ro_get_markup_account(
                product=self.product_id
            )
            deferred_vat_account = location._l10n_ro_get_deferred_vat_account(
                product=self.product_id
            )
            if not markup_account or not deferred_vat_account:
                raise UserError(
                    self.env._(
                        "Missing markup (378) or deferred VAT (4428) account "
                        "for product %(p)s at location %(l)s.",
                        p=self.product_id.display_name,
                        l=location.display_name,
                    )
                )
            if direction == "in":
                markup_total, vat_total = self._l10n_ro_retail_in_amounts(
                    location, warehouse, qty
                )
            else:
                markup_total, vat_total = self._l10n_ro_retail_out_amounts(
                    location, warehouse, qty
                )
            markup_total = currency.round(markup_total)
            vat_total = currency.round(vat_total)
            sign = 1 if direction == "in" else -1
            ledger_vals.append(
                {
                    "company_id": self.company_id.id,
                    # The same date the entry is posted on, so the ledger
                    # and the general ledger can be read side by side. A
                    # backdated posting has to produce a backdated row, or
                    # the report as of a past date answers for the wrong
                    # moment.
                    "date": self._l10n_ro_retail_ledger_date(),
                    "product_id": self.product_id.id,
                    "location_id": location.id,
                    "quantity": sign * qty,
                    # The cost rides along so a row states everything the
                    # event did to 371: cost + markup + VAT is the shelf
                    # value that went on or came off.
                    "cost": sign * currency.round(abs(self.value)),
                    "markup": sign * markup_total,
                    "vat": sign * vat_total,
                    "origin_type": "move",
                    "move_id": self.id,
                    "reference": self.reference or self.name,
                }
            )
            if not float_is_zero(markup_total, precision_rounding=currency.rounding):
                aml_vals += self._l10n_ro_retail_amls(
                    direction, stock_account, markup_account, markup_total
                )
            if not float_is_zero(vat_total, precision_rounding=currency.rounding):
                aml_vals += self._l10n_ro_retail_amls(
                    direction, stock_account, deferred_vat_account, vat_total
                )
        return aml_vals

    def _l10n_ro_retail_ledger_date(self):
        """Accounting date of the retail entry for this move."""
        self.ensure_one()
        forced = self.env.context.get("force_period_date")
        if forced:
            return fields.Datetime.to_datetime(forced)
        return self.date or fields.Datetime.now()

    def _l10n_ro_retail_amls(self, direction, stock_account, other_account, amount):
        """Build the two-line AML pair for a retail entry.

        Direction 'in':  Dr stock_account / Cr other_account
        Direction 'out': Dr other_account / Cr stock_account
        """
        self.ensure_one()
        sign = 1 if direction == "in" else -1
        signed = sign * amount
        debit_account = stock_account if signed > 0 else other_account
        credit_account = other_account if signed > 0 else stock_account
        abs_value = abs(signed)
        base = {
            "name": self.reference or self.name,
            "product_id": self.product_id.id,
            "quantity": self.product_qty,
        }
        return [
            dict(base, account_id=debit_account.id, debit=abs_value, credit=0.0),
            dict(base, account_id=credit_account.id, debit=0.0, credit=abs_value),
        ]

    def _create_account_move_ro_extra(self):
        account_moves = super()._create_account_move_ro_extra()
        Ledger = self.env["l10n.ro.retail.markup.line"].sudo()
        for move in self.filtered(lambda m: m.is_l10n_ro_record):
            if move.l10n_ro_retail_markup_line_ids:
                # Already booked. The base module calls this once per move, but
                # a second pass would load the markup twice and there is nothing
                # in the entry itself that would show it.
                continue
            ledger_vals = []
            aml_vals_list = move._l10n_ro_get_retail_aml_vals(ledger_vals)
            if not ledger_vals:
                continue
            account_move = self.env["account.move"]
            if aml_vals_list:
                journal = move.company_id.account_stock_journal_id
                if not journal:
                    raise UserError(
                        self.env._(
                            "No stock journal defined on company %(company)s.",
                            company=move.company_id.display_name,
                        )
                    )
                account_move = self.env["account.move"].create(
                    {
                        "l10n_ro_extra_stock_move_id": move.id,
                        "journal_id": journal.id,
                        "line_ids": [Command.create(v) for v in aml_vals_list],
                        "date": self.env.context.get("force_period_date")
                        or fields.Date.context_today(self),
                        "ref": self.env._(
                            "Retail markup %(ref)s", ref=move.reference or move.name
                        ),
                    }
                )
                account_move._post()
                account_moves |= account_move
            for vals in ledger_vals:
                vals["account_move_id"] = account_move.id or False
            Ledger.create(ledger_vals)
        return account_moves
