from datetime import datetime

from odoo import models
from odoo.fields import Date


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_l10n_ro_distrib_landed_cost(self, at_date=None):
        domain = [("move_id", "in", self.ids), ("cost_id.state", "=", "done")]
        if at_date:
            domain.append(("cost_id.date", "<=", at_date))
        landed_cost_group = self.env[
            "l10n.ro.stock.valuation.adjustment.lines"
        ]._read_group(domain, ["move_id"], ["id:recordset"])
        return dict(landed_cost_group)

    def _l10n_ro_get_redistributed_landed_cost(self, at_date=None):
        """Landed cost of the origin move that was redistributed onto self."""
        self.ensure_one()
        domain = [
            ("move_id", "=", self.id),
            ("origin_line_id.move_id", "in", self.move_orig_ids.ids),
            ("cost_id.state", "=", "done"),
            ("cost_id.l10n_ro_only_on_distributed_lines", "=", False),
        ]
        if at_date:
            domain.append(("cost_id.date", "<=", at_date))
        lines = self.env["l10n.ro.stock.valuation.adjustment.lines"].search(domain)
        return sum(lines.mapped("additional_landed_cost"))

    def _get_value_from_origin_move(
        self,
        quantity,
        forced_std_price=False,
        at_date=False,
        ignore_manual_update=False,
    ):
        """Keep the landed cost from being counted twice on an untracked step.

        A move whose consumption is tracked is valued at what it took out of
        the stack back then, so nothing of what was booked afterwards is in
        it.  A move that consumed nothing has no such record and falls back
        on the origin move, whose value has meanwhile grown by the landed
        cost - the very amount handed to this move again on its own
        distributed line.  Take it out of the inherited value, so that the
        two routes end up telling the same story.
        """
        res = super()._get_value_from_origin_move(
            quantity,
            forced_std_price=forced_std_price,
            at_date=at_date,
            ignore_manual_update=ignore_manual_update,
        )
        if not res or self.l10n_ro_move_track_src_ids or not self.move_orig_ids:
            return res
        redistributed = self._l10n_ro_get_redistributed_landed_cost(at_date=at_date)
        if not redistributed:
            return res
        valued_qty = self._get_valued_qty()
        ratio = quantity / valued_qty if valued_qty else 0
        res["value"] -= ratio * redistributed
        return res

    def _get_value_from_extra(self, quantity, at_date=None):
        self.ensure_one()
        accounting_data = super()._get_value_from_extra(quantity, at_date=at_date)
        # Add landed costs value
        lcs = self._get_l10n_ro_distrib_landed_cost(at_date=at_date)
        lcs = lcs.get(self)
        if not lcs:
            return accounting_data
        lcs_desc = []
        for lc in lcs:
            accounting_data["value"] += lc.additional_landed_cost
            landed_cost = lc.cost_id
            value = lc.additional_landed_cost
            vendor_bill = landed_cost.vendor_bill_id
            if vendor_bill:
                desc = self.env._(
                    "+ %(value)s from %(vendor_bill)s (Landed Cost: %(landed_cost)s)",
                    value=self.company_currency_id.format(value),
                    vendor_bill=vendor_bill.display_name,
                    landed_cost=landed_cost.display_name,
                )
            else:
                desc = self.env._(
                    "+ %(value)s (Landed Cost: %(landed_cost)s)",
                    value=self.company_currency_id.format(value),
                    landed_cost=landed_cost.display_name,
                )
            lcs_desc.append(desc)
        description = self.env._(
            "Additional landed costs:\n%(landed_cost)s", landed_cost="\n".join(lcs_desc)
        )
        if not accounting_data["description"]:
            accounting_data["description"] = description
        else:
            accounting_data["description"] += "\n" + description
        return accounting_data

    def _get_value_from_account_move(self, quantity, at_date=None):
        """For Romania if it has an accounting entry, take the value from there.
        For landed cost distribution will take real value, not value from standard
        price, which can be different.
        """
        valuation_data = super()._get_value_from_account_move(quantity, at_date=at_date)
        if not (self.is_l10n_ro_record and self.account_move_id and self._is_out()):
            return valuation_data

        if isinstance(at_date, datetime):
            # Since aml.date are Date, we don't need the extra precision here.
            at_date = Date.to_date(at_date)

        if self.account_move_id.state != "posted":
            return valuation_data
        if at_date and self.account_move_id.date > at_date:
            return valuation_data
        quantity = quantity or self.quantity
        value = self.account_move_id.amount_total_signed
        if self.l10n_ro_move_type == "internal_transfer":
            value = value / 2
        valuation_data["quantity"] = quantity
        valuation_data["value"] = value
        valuation_data["description"] = self.env._(
            "%(value)s for %(quantity)s %(unit)s from %(bills)s",
            value=self.company_currency_id.format(value),
            quantity=quantity,
            unit=self.product_id.uom_id.name,
            bills=self.account_move_id.display_name,
        )
        return valuation_data
