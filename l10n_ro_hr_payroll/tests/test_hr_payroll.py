# Copyright (C) 2020 OdooERP România S.R.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from .common import TestHrEmployee
from datetime import datetime
from dateutil.relativedelta import relativedelta


class TestHrPayroll(TestHrEmployee):
    def test_get_worked_day_lines(self):
        def was_on_leave(employee_id, datetime_day):
            res = False
            day = datetime_day.strftime("%Y-%m-%d")
            res = self.env['hr.holidays'].search([
                ('state', '=', 'validate'),
                ('employee_id', '=', employee_id),
                ('type', '=', 'remove'),
                ('date_from', '<=', day),
                ('date_to', '>=', day)])
            return res

        date_from = datetime.today() + relativedelta(day=1)

        first_day = datetime.strftime(
            datetime.today() + relativedelta(day=1), '%Y-%m-%d')
        last_day = datetime.strftime(
            datetime.today() + relativedelta(day=1, months=1, days=-1),
            '%Y-%m-%d'
        )
        nb_of_days = datetime.strptime(last_day, '%Y-%m-%d').day

        total = attendances = 0
        for day in range(0, nb_of_days):
            total_day = date_from + relativedelta(days=day)

            if total_day.weekday() < 5:
                total += 1

            if was_on_leave(self.test_employee_1.id, total_day) and \
                    total_day.weekday() < 5:
                attendances += 1

        payslip = self.env['hr.payslip'].create({
            'employee_id': self.test_employee_1.id,
            'date_from': first_day,
            'date_to': last_day
        })

        with self.env.do_in_onchange():
            payslip.onchange_employee()
            worked_line = payslip.worked_days_line_ids

            sl1_line = worked_line.filtered(lambda w: w.code == 'SL1')
            work100_line = worked_line.filtered(lambda w: w.code == 'WORK100')

            self.assertEqual(sl1_line.number_of_days, attendances)
            self.assertEqual(sl1_line.number_of_hours, attendances * 8)

            self.assertEqual(work100_line.number_of_days,
                             total - attendances)
            self.assertEqual(work100_line.number_of_hours,
                             (total - attendances) * 8)

            self.assertEqual(payslip.working_days, total)

        income_date_from = datetime.strftime(
            datetime.today() + relativedelta(day=1, months=-2), '%Y-%m-%d'
        )
        income_date_to = datetime.strftime(
            datetime.today() + relativedelta(day=1, months=-1, days=-1),
            '%Y-%m-%d',
        )
        income03 = self.env['hr.employee.income'].create({
            'number_of_days': 22,
            'number_of_hours': 176,
            'gross_amount': 2640.00,
            'net_amount': 2300.00,
            'date_from': income_date_from,
            'date_to': income_date_to,
            'employee_id': self.test_employee_1.id
        })

        with self.env.do_in_onchange():
            income03.payslip_id = payslip
            income03._onchange_payslip_id()
            self.assertEqual(income03.number_of_days, total)
            self.assertEqual(income03.number_of_hours, total * 8)
            self.assertEqual(income03.date_from, income_date_from)
            self.assertEqual(income03.date_to, income_date_to)
