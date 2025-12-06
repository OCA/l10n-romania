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
