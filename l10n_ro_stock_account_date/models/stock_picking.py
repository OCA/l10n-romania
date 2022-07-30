# Copyright (C) 2022 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class StockPicking(models.Model):
    _inherit = "stock.picking"

    accounting_date = fields.Datetime(
        "Accounting Date",
        copy=False,
        help="If this field is set, the svl and accounting entries will "
        "have this date, If not will have the today date as it should be",
        tracking=True,
    )

    def check_accounting_date(self, accounting_date=None):
        date = accounting_date or self.accounting_date.date()
        # if date > fields.date.today():
        #     raise ValidationError(
        #         _(
        #             "You can not have a Accounting date=%s for picking bigger than today!"
        #             % date
        #         )
        #     )
        get_param = self.env["ir.config_parameter"].sudo().get_param
        restrict_date = safe_eval(
            get_param("restrict_stock_move_date_last_months", "False")
        )
        if restrict_date:
            today = fields.Date.context_today(self)
            start_day_of_prev_month = today + relativedelta(day=1, months=-1, days=0)
            end_day_of_current_month = today + relativedelta(day=1, months=1, days=-1)

            if not start_day_of_prev_month <= date <= end_day_of_current_month:
                raise ValidationError(
                    _("Cannot validate stock move due to date restriction.")
                )

    def _action_done(self):
        """Update date_done from accounting_date field"""
        res = super()._action_done()
        for picking in self:
            if picking.accounting_date:
                self.check_accounting_date()
                picking.write({"date_done": picking.accounting_date})
        return res
