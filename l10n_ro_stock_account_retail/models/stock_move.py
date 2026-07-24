# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


class StockMove(models.Model):
    _inherit = "stock.move"

    def _l10n_ro_retail_legs(self):
        """Return a list of (direction, location, warehouse) legs to book
        for this move.

        - ('in', dest_loc, dest_wh)  when goods enter a retail location
        - ('out', src_loc, src_wh)   when goods leave a retail location

        A move between two retail warehouses with different pricelists
        produces both an 'out' (at source warehouse pricing) and an 'in'
        (at destination warehouse pricing) leg.
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

    def _l10n_ro_get_retail_aml_vals(self):
        """Return AML values that book the markup (378) and deferred VAT
        (4428) for the retail-crossing legs of this stock move."""
        self.ensure_one()
        if not self.is_l10n_ro_record:
            return []
        legs = self._l10n_ro_retail_legs()
        if not legs:
            return []
        qty = self.product_qty
        currency = self.company_id.currency_id
        if float_is_zero(qty, precision_rounding=self.product_id.uom_id.rounding):
            return []
        cost_total = abs(self.value)
        cost_per_unit = cost_total / qty if qty else 0.0
        aml_vals = []
        for direction, location, warehouse in legs:
            stock_account = (
                location.l10n_ro_property_stock_valuation_account_id
                or self.product_id.l10n_ro_property_stock_valuation_account_id
                or self.product_id.categ_id.property_stock_valuation_account_id
            )
            if not stock_account:
                continue
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
            prices = self.product_id.product_tmpl_id._l10n_ro_get_retail_prices(
                warehouse=warehouse, company=self.company_id
            )
            markup_per_unit = prices["price_without_vat"] - cost_per_unit
            vat_per_unit = prices["vat"]
            markup_total = currency.round(markup_per_unit * qty)
            vat_total = currency.round(vat_per_unit * qty)
            if not float_is_zero(markup_total, precision_rounding=currency.rounding):
                aml_vals += self._l10n_ro_retail_amls(
                    direction, stock_account, markup_account, markup_total
                )
            if not float_is_zero(vat_total, precision_rounding=currency.rounding):
                aml_vals += self._l10n_ro_retail_amls(
                    direction, stock_account, deferred_vat_account, vat_total
                )
        return aml_vals

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
        for move in self.filtered(lambda m: m.is_l10n_ro_record):
            aml_vals_list = move._l10n_ro_get_retail_aml_vals()
            if not aml_vals_list:
                continue
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
        return account_moves
