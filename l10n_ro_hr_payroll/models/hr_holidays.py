# Copyright (C) 2014 Adrian Vasile
# Copyright (C) 2018 FOREST AND BIOMASS ROMANIA SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class HRHolidays(models.Model):
    _inherit = 'hr.holidays'

    @api.one
    @api.depends('date_from', 'date_to', 'holiday_status_id')
    def _get_holiday_daily_base(self):
        daily_base = 0
        if not self.is_unpaid:
            if self.is_sick_leave:
                if self.initial_id:
                    daily_base = self.initial_id.daily_base
                else:
                    daily_base = self.employee_id._get_holiday_base(
                        date=self.date_from, month_no=6)
                    daily_base = \
                        daily_base * self.holiday_status_id.percentage / 100
                self.employer_amount = self.employer_days * daily_base
                self.budget_amount = self.budget_days * daily_base
                self.total_amount = self.number_of_days_temp * daily_base
            else:
                daily_base = self.employee_id._get_holiday_base(
                    date=self.date_from, month_no=3)
        self.daily_base = daily_base

    daily_base = fields.Float('Daily Base',
                              compute='_get_holiday_daily_base',
                              store=True)
    employer_amount = fields.Float('Amount by Employer',
                                   compute='_get_holiday_daily_base',
                                   store=True)
    budget_amount = fields.Float('Amount by Social Sevcurity',
                                 compute='_get_holiday_daily_base',
                                 store=True)
    total_amount = fields.Float('Total Amount',
                                compute='_get_holiday_daily_base',
                                store=True)
