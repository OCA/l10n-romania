# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    l10n_ro_retail_markup_line_ids = fields.One2many(
        "l10n.ro.retail.markup.line",
        "landed_cost_id",
        string="Retail Markup Ledger",
        readonly=True,
    )

    def button_validate(self):
        res = super().button_validate()
        self._l10n_ro_retail_rebalance()
        return res

    # ------------------------------------------------------------------
    def _l10n_ro_retail_adjustments(self):
        """Return ``[(move, amount)]`` for the parts of this landed cost that
        landed on goods currently held in a shop.

        Both sets of adjustment lines are read, but the source line only
        contributes what stayed on it. A landed cost distributed only on
        destinations - a purchase price difference - has its source amounts
        zeroed by the base module and carries everything on the Romanian
        distributed lines. An ordinary one - transport, DVI - does not: the
        source line keeps the whole amount **and** distributed lines are
        created for the portion that has since moved on.

        Reading both at face value therefore counted that portion twice, and
        it is not a hypothetical: a shop that receives its own goods and sends
        part of them to another shop is a chain a retail network runs weekly.
        The reception line and the transfer line are both retail, so 378 of
        the receiving shop was relieved by the whole amount while 371 had only
        kept the part that stayed - the invariant this module exists to hold
        broke, quietly. The base module posts the source amount in full on the
        receiving shop's 371 and then moves the consumed portion across to the
        other shop's, so what each shop has to give back is exactly what its
        own 371 kept.

        Lines whose destination is not a retail location are left out on
        purpose: goods that have already been sold carry their extra cost on
        607, where it belongs, and goods in a plain warehouse are valued at
        cost anyway.
        """
        self.ensure_one()
        rounding = self.currency_id.rounding
        result = []
        for line in self.valuation_adjustment_lines:
            move = line.move_id
            if not move or not move.location_dest_id.l10n_ro_retail:
                continue
            if self.l10n_ro_only_on_distributed_lines:
                # Nothing left here: the base module moved the whole amount
                # onto the distributed lines and zeroed this one.
                continue
            amount = line.additional_landed_cost - sum(
                line.l10n_ro_distributed_valuation_lines.mapped(
                    "additional_landed_cost"
                )
            )
            if float_is_zero(amount, precision_rounding=rounding):
                continue
            result.append((move, amount))
        for line in self.l10n_ro_distributed_valuation_lines:
            move = line.move_id
            if not move or not move.location_dest_id.l10n_ro_retail:
                continue
            amount = line.additional_landed_cost
            if float_is_zero(amount, precision_rounding=rounding):
                continue
            result.append((move, amount))
        return result

    def _l10n_ro_retail_origin_type(self):
        self.ensure_one()
        if self.l10n_ro_cost_type == "price_diff":
            return "price_difference"
        return "landed_cost"

    def _l10n_ro_retail_rebalance(self):
        """Move the extra cost out of the markup so 371 stays at shelf price.

        The landed cost has already debited 371 with the extra cost. For a shop
        that value is fixed - it is the price on the label - so the same amount
        is taken off 378: the cost of the goods went up and the markup they
        carry went down, the shelf price unchanged.

        Nothing is done to the deferred VAT: the VAT inside the shelf price
        depends on the price, not on the cost.
        """
        for cost in self.filtered(lambda c: c.is_l10n_ro_record):
            if cost.l10n_ro_retail_markup_line_ids:
                # Already given back. Core refuses to validate a landed cost
                # twice, so this cannot happen today - but the correction
                # leaves no trace in its own entry that would show a second
                # pass, and the rest of the family guards itself the same way.
                continue
            adjustments = cost._l10n_ro_retail_adjustments()
            if not adjustments:
                continue
            cost._l10n_ro_retail_check_markup(adjustments)
            aml_vals = []
            ledger_vals = []
            for move, amount in adjustments:
                aml_vals += cost._l10n_ro_retail_aml_pair(move, amount)
                ledger_vals.append(cost._l10n_ro_retail_ledger_vals(move, amount))
            if not aml_vals:
                continue
            journal = (
                cost.account_journal_id or cost.company_id.account_stock_journal_id
            )
            if not journal:
                raise UserError(
                    cost.env._(
                        "No journal to post the retail markup correction of "
                        "%(cost)s on.",
                        cost=cost.display_name,
                    )
                )
            account_move = self.env["account.move"].create(
                {
                    "journal_id": journal.id,
                    "date": cost.date,
                    "ref": cost.env._(
                        "Retail markup correction %(cost)s", cost=cost.name
                    ),
                    "line_ids": [Command.create(vals) for vals in aml_vals],
                }
            )
            account_move._post()
            for vals in ledger_vals:
                vals["account_move_id"] = account_move.id
            self.env["l10n.ro.retail.markup.line"].sudo().create(ledger_vals)

    def _l10n_ro_retail_check_markup(self, adjustments):
        """Refuse a landed cost that would leave the goods costing more than
        they are priced at."""
        self.ensure_one()
        Ledger = self.env["l10n.ro.retail.markup.line"]
        rounding = self.currency_id.rounding
        per_warehouse = {}
        for move, amount in adjustments:
            warehouse = move.location_dest_id.warehouse_id
            key = (warehouse, move.product_id)
            per_warehouse[key] = per_warehouse.get(key, 0.0) + amount
        for (warehouse, product), amount in per_warehouse.items():
            if warehouse.l10n_ro_retail_allow_negative_markup:
                continue
            markup, _vat = Ledger._l10n_ro_carried(warehouse, product, self.company_id)
            if float_compare(markup - amount, 0.0, precision_rounding=rounding) >= 0:
                continue
            qty = Ledger._l10n_ro_carried_qty(warehouse, product, self.company_id)
            shortfall = amount - markup
            raise UserError(
                self.env._(
                    "%(cost)s adds %(amount).2f of cost to %(product)s in "
                    "%(warehouse)s, which carries only %(markup).2f of markup: "
                    "the goods would cost more than they are priced at.\n\n"
                    "Raise the shelf price by at least %(per_unit).2f a unit "
                    "with a retail price change before validating, "
                    "or tick 'Allow Selling Below Cost' on the warehouse if "
                    "the shop genuinely sells this below cost.",
                    cost=self.display_name,
                    amount=amount,
                    product=product.display_name,
                    warehouse=warehouse.display_name,
                    markup=markup,
                    per_unit=(shortfall / qty) if qty else shortfall,
                )
            )

    def _l10n_ro_retail_aml_pair(self, move, amount):
        """``Dr 378 / Cr 371`` for the extra cost, sides swapped on a credit."""
        self.ensure_one()
        location = move.location_dest_id
        product = move.product_id
        stock_account = location._l10n_ro_get_stock_account(product=product)
        markup_account = location._l10n_ro_get_markup_account(product=product)
        if not stock_account or not markup_account:
            raise UserError(
                self.env._(
                    "Missing stock valuation (371) or markup (378) account for "
                    "product %(product)s at location %(location)s.",
                    product=product.display_name,
                    location=location.display_name,
                )
            )
        debit_account = markup_account if amount > 0 else stock_account
        credit_account = stock_account if amount > 0 else markup_account
        value = self.currency_id.round(abs(amount))
        base = {
            "name": self.env._(
                "Retail markup correction %(ref)s", ref=move.reference or move.name
            ),
            "product_id": product.id,
            "quantity": move.product_qty,
        }
        return [
            dict(base, account_id=debit_account.id, debit=value, credit=0.0),
            dict(base, account_id=credit_account.id, debit=0.0, credit=value),
        ]

    def _l10n_ro_retail_ledger_vals(self, move, amount):
        self.ensure_one()
        return {
            "company_id": self.company_id.id,
            "date": self.date,
            "product_id": move.product_id.id,
            "location_id": move.location_dest_id.id,
            # No goods move: only the split between cost and markup changes,
            # which is why the two cancel out and 371 stays where it was.
            "quantity": 0.0,
            "cost": self.currency_id.round(amount),
            "markup": -self.currency_id.round(amount),
            "vat": 0.0,
            "origin_type": self._l10n_ro_retail_origin_type(),
            "landed_cost_id": self.id,
            "move_id": move.id,
            "reference": self.name,
        }
