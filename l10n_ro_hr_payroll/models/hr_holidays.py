# Copyright (C) 2014 Adrian Vasile
# Copyright (C) 2018 FOREST AND BIOMASS ROMANIA SA
# Copyright (C) 2020 OdooERP România S.R.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
from datetime import datetime


class HRHolidays(models.Model):
    _inherit = 'hr.holidays'

    @api.multi
    @api.depends('date_from', 'date_to', 'holiday_status_id')
    def _compute_holiday_amounts(self):
        for holiday in self:
            daily_base = 0

            if not holiday.is_unpaid:
                if holiday.is_sick_leave:
                    if holiday.initial_id:
                        daily_base = holiday.initial_id.daily_base
                    else:
                        daily_base = holiday.employee_id._get_holiday_base(
                            date=holiday.date_from, month_no=6)
                        if daily_base == 0:
                            gross = holiday.employee_id.contract_id.wage
                            date_from = \
                                datetime.strptime(holiday.date_from[:10],
                                                  "%Y-%m-%d") + \
                                relativedelta(day=1)
                            last_day = \
                                datetime.strptime(holiday.date_from[:10],
                                                  "%Y-%m-%d") + \
                                relativedelta(day=1, months=1, days=-1)
                            nb_of_days = last_day.day
                            total = 0
                            for day in range(0, nb_of_days):
                                total_day = date_from + \
                                    relativedelta(days=day)

                                if total_day.weekday() < 5:
                                    total += 1
                            daily_base = gross / total
                        daily_base = \
                            daily_base * \
                            holiday.holiday_status_id.percentage / 100

                    holiday.employer_amount = \
                        holiday.employer_days * daily_base
                    holiday.budget_amount =\
                        holiday.budget_days * daily_base
                    holiday.total_amount = \
                        holiday.number_of_days_temp * daily_base
                else:
                    daily_base = holiday.employee_id._get_holiday_base(
                        date=holiday.date_from, month_no=3)
            holiday.daily_base = daily_base

    daily_base = fields.Float(
        'Daily Base', compute='_compute_holiday_amounts', store=True)
    employer_amount = fields.Float(
        'Amount by Employer', compute='_compute_holiday_amounts', store=True)
    budget_amount = fields.Float(
        'Amount by Social Security',
        compute='_compute_holiday_amounts', store=True)
    total_amount = fields.Float(
        'Total Amount', compute='_compute_holiday_amounts', store=True)
