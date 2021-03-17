# Copyright (C) 2020 OdooERP România S.R.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from .common import TestHrEmployee
from dateutil.relativedelta import relativedelta
from datetime import datetime


class TestHrHolidays(TestHrEmployee):

    def test_compute_medical_amounts(self):
        self.assertEqual(self.initleave.daily_base, 105)
        self.assertEqual(self.initleave.employer_days, 5)
        self.assertEqual(self.initleave.employer_amount, 525)
        self.assertEqual(self.initleave.budget_amount, 210)
        self.assertEqual(self.initleave.budget_days, 2)
        self.assertEqual(self.initleave.total_amount, 735)

        self.assertEqual(self.leave.daily_base, 105)
        self.assertEqual(self.leave.employer_days, 0)
        self.assertEqual(self.leave.employer_amount, 0)
        self.assertEqual(self.leave.budget_amount, 315)
        self.assertEqual(self.leave.budget_days, 3)
        self.assertEqual(self.leave.total_amount, 315)

        date_from = datetime.today() + relativedelta(day=1)

        leave1 = self.env['hr.holidays'].create(
            {'name': 'Med1',
             'holiday_status_id': self.leave01.id,
             'date_from': datetime.strftime(
                 date_from + relativedelta(months=-3),
                 '%Y-%m-%d'),
             'date_to': (date_from +
                         relativedelta(day=4, months=-3)).strftime(
                 '%Y-%m-%d 18:00:00'),
             'type': 'remove',
             'employee_id': self.test_employee_1.id,
             'disease_id': self.disease1.id,
             'number_of_days_temp': 4
             })
        daily_base = leave1.employee_id._get_holiday_base(
            date=leave1.date_from, month_no=6)
        daily_base = daily_base * leave1.holiday_status_id.percentage / 100

        self.assertAlmostEqual(leave1.daily_base, daily_base)
        self.assertEqual(leave1.employer_days, 4)
        self.assertAlmostEqual(leave1.employer_amount, 4 * daily_base)
        self.assertEqual(leave1.budget_amount, 0)
        self.assertEqual(leave1.budget_days, 0)
        self.assertAlmostEqual(leave1.total_amount, 4 * daily_base)

        leave2 = self.env['hr.holidays'].create(
            {'name': 'Med1',
             'holiday_status_id': self.leave01.id,
             'date_from': datetime.strftime(
                 date_from + relativedelta(months=-25),
                 '%Y-%m-%d'),
             'date_to': (date_from +
                         relativedelta(day=4, months=-25)).strftime(
                 '%Y-%m-%d 18:00:00'),
             'type': 'remove',
             'employee_id': self.test_employee_1.id,
             'disease_id': self.disease1.id,
             'number_of_days_temp': 4
             })
        gross = leave2.employee_id.contract_id.wage
        date_from = \
            datetime.strptime(leave2.date_from[:10], "%Y-%m-%d") + \
            relativedelta(day=1)
        last_day = \
            datetime.strptime(leave2.date_from[:10], "%Y-%m-%d") + \
            relativedelta(day=1, months=1, days=-1)
        nb_of_days = last_day.day
        total = 0
        for day in range(0, nb_of_days):
            total_day = date_from + \
                relativedelta(days=day)

            if total_day.weekday() < 5:
                total += 1
        daily_base = (gross / total) * self.leave01.percentage / 100

        self.assertAlmostEqual(leave2.daily_base, daily_base)
        self.assertEqual(leave2.employer_days, 4)
        self.assertAlmostEqual(leave2.employer_amount, 4 * daily_base)
        self.assertEqual(leave2.budget_amount, 0)
        self.assertEqual(leave2.budget_days, 0)
        self.assertAlmostEqual(leave2.total_amount, 4 * daily_base)
