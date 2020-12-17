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

        def change_in_hour(hour_from, hour_to):
            diff = hour_to - hour_from
            minutes = (diff.seconds + diff.microseconds / 1000000.0) / 60
            hours = minutes / 60
            minutes -= hours * 60
            res = (hours + minutes / 60)
            return res

        date_from = datetime.today() + relativedelta(day=1)

        first_day = datetime.strftime(
            datetime.today() + relativedelta(day=1), '%Y-%m-%d')
        last_day = datetime.strftime(
            datetime.today() + relativedelta(day=1, months=1, days=-1),
            '%Y-%m-%d'
        )
        nb_of_days = datetime.strptime(last_day, '%Y-%m-%d').day

        attendance_obj = self.env['hr.attendance']
        # weekend
        attendance_obj.create({
            'employee_id': self.test_employee_1.id,
            'department_id': self.test_employee_1.department_id.id,
            'check_in': '2020-11-01 18:00:00',
            'check_out': '2020-11-01 20:00:00',
            'worked_hours': 2
        })
        # holiday
        attendance_obj.create({
            'employee_id': self.test_employee_1.id,
            'department_id': self.test_employee_1.department_id.id,
            'check_in': '2020-11-30 18:00:00',
            'check_out': '2020-11-30 20:00:00',
            'worked_hours': 2
        })
        # night and overtime
        attendance_obj.create({
            'employee_id': self.test_employee_1.id,
            'department_id': self.test_employee_1.department_id.id,
            'check_in': '2020-11-02 09:00:00',
            'check_out': '2020-11-02 18:00:00',
            'worked_hours': 9
        })
        attendance_obj.create({
            'employee_id': self.test_employee_1.id,
            'department_id': self.test_employee_1.department_id.id,
            'check_in': '2020-11-03 20:00:00',
            'check_out': '2020-11-03 23:00:00',
            'worked_hours': 3
        })
        attendance_obj.create({
            'employee_id': self.test_employee_1.id,
            'department_id': self.test_employee_1.department_id.id,
            'check_in': '2020-11-04 08:00:00',
            'check_out': '2020-11-04 23:00:00',
            'worked_hours': 15
        })
        attendance_obj.create({
            'employee_id': self.test_employee_1.id,
            'department_id': self.test_employee_1.department_id.id,
            'check_in': '2020-11-06 18:00:00',
            'check_out': '2020-11-07 04:00:00',
            'worked_hours': 11
        })
        attendance_obj.create({
            'employee_id': self.test_employee_1.id,
            'department_id': self.test_employee_1.department_id.id,
            'check_in': '2020-11-09 15:00:00',
            'check_out': '2020-11-10 02:00:00',
            'worked_hours': 9
        })

        total = attendances = 0
        holiday = weekend = overtime = 0

        for day in range(0, nb_of_days):
            total_day = date_from + relativedelta(days=day)
            public_holiday = self.env['hr.holidays.public.line'].search(
                [('date', '=', total_day)])
            if total_day.weekday() < 5 and not public_holiday:
                total += 1

            if was_on_leave(self.test_employee_1.id, total_day) and \
                    total_day.weekday() < 5 and not public_holiday:
                attendances += 1

        att = self.env['hr.attendance'].search(
            [('check_in', '>=', first_day),
             ('check_out', '<=', last_day),
             ('employee_id', '=', self.test_employee_1.id)])
        for att in att:
            hour_from = datetime.strptime(att.check_in, '%Y-%m-%d %H:%M:%S')
            hour_to = datetime.strptime(att.check_out, '%Y-%m-%d %H:%M:%S')
            public_holiday = self.env['hr.holidays.public.line'].search(
                [('date', '=', hour_from)])
            if hour_from.weekday() >= 5 and not public_holiday:
                weekend += change_in_hour(hour_from, hour_to)
            if public_holiday:
                holiday += change_in_hour(hour_from, hour_to)

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
            holiday_line = worked_line.filtered(lambda w: w.code == 'HOLIDAY')
            weekend_line = worked_line.filtered(lambda w: w.code == 'WEEKEND')
            supl_line = worked_line.filtered(lambda w: w.code == 'SUPL')
            night_line = worked_line.filtered(lambda w: w.code == 'NIGHT')

            self.assertEqual(sl1_line.number_of_days, attendances)
            self.assertEqual(sl1_line.number_of_hours, attendances * 8)

            self.assertEqual(work100_line.number_of_days,
                             total - attendances)
            self.assertEqual(work100_line.number_of_hours,
                             (total - attendances) * 8)

            self.assertEqual(payslip.working_days, total)

            self.assertEqual(holiday_line.number_of_hours, holiday)
            self.assertEqual(weekend_line.number_of_hours, weekend)

            self.assertEqual(supl_line.number_of_hours, 0)
            self.assertEqual(night_line.number_of_hours, 0)
            overtime += supl_line.number_of_hours + night_line.number_of_hours

        income_date_from = datetime.strftime(
            datetime.today() + relativedelta(day=1, months=-2), '%Y-%m-%d'
        )
        income_date_to = datetime.strftime(
            datetime.today() + relativedelta(day=1, months=-1, days=-1),
            '%Y-%m-%d',
        )

        incomes = self.env['hr.employee.income'].search([
            ('payslip_id', '=', payslip.id)
        ])
        self.assertFalse(incomes)

        payslip.action_payslip_done()
        incomes = self.env['hr.employee.income'].search([
            ('payslip_id', '=', payslip.id)
        ])
        self.assertTrue(incomes)
        self.assertEqual(len(incomes), 1)

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
            self.assertEqual(income03.number_of_hours, total * 8 +
                             holiday + weekend + overtime)
            self.assertEqual(income03.date_from, first_day)
            self.assertEqual(income03.date_to, last_day)

    def test_night_hours(self):
        first_day = datetime.strftime(
            datetime.today() + relativedelta(day=1), '%Y-%m-%d')
        last_day = datetime.strftime(
            datetime.today() + relativedelta(day=1, months=1, days=-1),
            '%Y-%m-%d'
        )

        payslip = self.env['hr.payslip'].create({
            'employee_id': self.test_employee_1.id,
            'date_from': first_day,
            'date_to': last_day
        })

        check_in = datetime(2020, 11, 9, 13, 0, 0)
        check_out = datetime(2020, 11, 10, 2, 0, 0)
        self.assertEqual(payslip.night_hours(check_in, check_out), 4)

        check_in = datetime(2020, 11, 9, 18, 0, 0)
        check_out = datetime(2020, 11, 9, 23, 0, 0)
        self.assertEqual(payslip.night_hours(check_in, check_out), 1)

        check_in = datetime(2020, 11, 9, 22, 0, 0)
        check_out = datetime(2020, 11, 10, 6, 0, 0)
        self.assertEqual(payslip.night_hours(check_in, check_out), 8)

        check_in = datetime(2020, 11, 10, 0, 30, 0)
        check_out = datetime(2020, 11, 10, 5, 0, 0)
        self.assertEqual(payslip.night_hours(check_in, check_out), 4.5)

    def test_overtime(self):
        first_day = datetime.strftime(
            datetime.today() + relativedelta(day=1), '%Y-%m-%d')
        last_day = datetime.strftime(
            datetime.today() + relativedelta(day=1, months=1, days=-1),
            '%Y-%m-%d'
        )

        payslip = self.env['hr.payslip'].create({
            'employee_id': self.test_employee_1.id,
            'date_from': first_day,
            'date_to': last_day
        })

        check_in = datetime(2020, 11, 9, 13, 0, 0)
        check_out = datetime(2020, 11, 10, 2, 0, 0)
        hour_from = check_in.replace(hour=8, minute=0)
        hour_to = check_in.replace(hour=17, minute=0)
        self.assertEqual(payslip.overtime(check_in, check_out, hour_from, hour_to), 5)

        check_in = datetime(2020, 11, 9, 18, 0, 0)
        check_out = datetime(2020, 11, 9, 23, 0, 0)
        hour_from = check_in.replace(hour=8, minute=0)
        hour_to = check_in.replace(hour=17, minute=0)
        self.assertEqual(payslip.overtime(check_in, check_out, hour_from, hour_to), 4)

        check_in = datetime(2020, 11, 9, 6, 0, 0)
        check_out = datetime(2020, 11, 9, 15, 0, 0)
        hour_from = check_in.replace(hour=8, minute=0)
        hour_to = check_in.replace(hour=17, minute=0)
        self.assertEqual(payslip.overtime(check_in, check_out, hour_from, hour_to), 2)

        check_in = datetime(2020, 11, 10, 6, 0, 0)
        check_out = datetime(2020, 11, 10, 10, 0, 0)
        hour_from = check_in.replace(hour=8, minute=0)
        hour_to = check_in.replace(hour=17, minute=0)
        self.assertEqual(payslip.overtime(check_in, check_out, hour_from, hour_to), 2)

        check_in = datetime(2020, 11, 10, 16, 0, 0)
        check_out = datetime(2020, 11, 10, 23, 0, 0)
        hour_from = check_in.replace(hour=8, minute=0)
        hour_to = check_in.replace(hour=17, minute=0)
        self.assertEqual(payslip.overtime(check_in, check_out, hour_from, hour_to), 5)
