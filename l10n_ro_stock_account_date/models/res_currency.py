# Copyright (C) 2024 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models


class Currency(models.Model):
    _inherit = "res.currency"

    # pylint: disable=W0622
    def _convert(self, from_amount, to_currency, company=None, date=None, round=True):
        force_period_date = self.env.context.get("force_period_date", False)
        if force_period_date:
            date = force_period_date
        return super()._convert(
            from_amount, to_currency, company=company, date=date, round=round
        )
