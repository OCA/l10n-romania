# Copyright (C) 2020 OdooERP România S.R.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime

from .common import TestHrEmployee


class TestHrEmployeeIncome(TestHrEmployee):
    def test_hr_employee_income(self):
        # Test employee income
        self.assertEqual(len(self.test_employee_1.income_ids), 2)

        date = datetime.today().strftime('%Y-%m-01')

        result1 = self.test_employee_1._get_holiday_base(date, 1)
        self.assertEqual(result1, 160)

        result2 = self.test_employee_1._get_holiday_base(date, 2)
        self.assertEqual(result2, 140)
