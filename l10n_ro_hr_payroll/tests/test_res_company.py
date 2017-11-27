# Copyright (C) 2020 OdooERP România S.R.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from .common import TestHrEmployee
from datetime import datetime
from dateutil.relativedelta import relativedelta


class TestResCompany(TestHrEmployee):
    def test_get_meal_voucher_value(self):
        company_meal_voucher_obj = self.env['res.company.meal.voucher']

        first_day = datetime.strftime(
            datetime.today() + relativedelta(day=1), '%Y-%m-%d'
        )

        next_month = datetime.strftime(
            datetime.today() + relativedelta(day=1, months=1), '%Y-%m-%d'
        )

        company_meal_voucher_obj.create({
            'company_id': self.env.user.company_id.id,
            'date_from': first_day,
            'value': 10
        })

        company_meal_voucher_obj.create({
            'company_id': self.env.user.company_id.id,
            'date_from': next_month,
            'value': 20
        })

        res_company = self.env.user.company_id

        self.assertEqual(
            res_company.get_meal_voucher_value(), 10)

        checkdate = '2010-06-12'
        self.assertEqual(
            res_company.get_meal_voucher_value(checkdate), 0)

        self.assertEqual(
            res_company.get_meal_voucher_value(next_month), 20)

        wage_history_obj = self.env['hr.wage.history']
        res_company_obj = self.env['res.company']

        wage_history_obj.create({
            'date': '2001-01-01',
            'min_wage': 800,
            'med_wage': 2000,
            'working_days': 20,
            'ceiling_min_wage': 8000
        })

        wage_history_obj.create({
            'date': '2002-01-01',
            'min_wage': 900,
            'med_wage': 2500,
            'working_days': 21,
            'ceiling_min_wage': 10100
        })

        wage_history_obj.create({
            'date': '2003-01-01',
            'min_wage': 1000,
            'med_wage': 3000,
            'working_days': 22,
            'ceiling_min_wage': 13000
        })

        date1 = datetime.strptime('2001-03-22', '%Y-%m-%d')
        self.assertEqual(res_company_obj.get_medium_wage(date1), 2000)
        self.assertEqual(res_company_obj.get_minimum_wage(date1), 800)
        self.assertEqual(res_company_obj.get_ceiling(date1), 8000)

        date2 = datetime.strptime('2002-08-14', '%Y-%m-%d')
        self.assertEqual(res_company_obj.get_medium_wage(date2), 2500)
        self.assertEqual(res_company_obj.get_minimum_wage(date2), 900)
        self.assertEqual(res_company_obj.get_ceiling(date2), 10100)

        date3 = datetime.strptime('2003-11-28', '%Y-%m-%d')
        self.assertEqual(res_company_obj.get_medium_wage(date3), 3000)
        self.assertEqual(res_company_obj.get_minimum_wage(date3), 1000)
        self.assertEqual(res_company_obj.get_ceiling(date3), 13000)
