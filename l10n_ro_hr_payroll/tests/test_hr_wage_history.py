# Copyright (C) 2020 OdooERP România S.R.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from .common import TestHrEmployee
from datetime import datetime


class TestHrWageHistory(TestHrEmployee):

    def test_get_wage_history(self):
        wage_history_obj = self.env['hr.wage.history']

        wage_history_obj.create({
            'date': '2011-01-01',
            'min_wage': 2230,
            'med_wage': 5429,
            'working_days': 20,
            'ceiling_min_wage': 155160
        })

        wage_history_obj.create({
            'date': '2012-01-01',
            'min_wage': 2130,
            'med_wage': 5229,
            'working_days': 21,
            'ceiling_min_wage': 149760
        })

        checkdate1 = datetime.strptime('2010-06-01', '%Y-%m-%d')
        self.assertEqual(wage_history_obj.get_medium_wage(checkdate1), 0)
        self.assertEqual(wage_history_obj.get_minimum_wage(checkdate1), 0)
        self.assertEqual(wage_history_obj.get_ceiling(checkdate1), 0)

        checkdate2 = datetime.strptime('2011-06-01', '%Y-%m-%d')
        self.assertEqual(wage_history_obj.get_medium_wage(checkdate2), 5429)
        self.assertEqual(wage_history_obj.get_minimum_wage(checkdate2), 2230)
        self.assertEqual(wage_history_obj.get_ceiling(checkdate2), 155160)

        checkdate3 = datetime.strptime('2012-02-12', '%Y-%m-%d')
        self.assertEqual(wage_history_obj.get_medium_wage(checkdate3), 5229)
        self.assertEqual(wage_history_obj.get_minimum_wage(checkdate3), 2130)
        self.assertEqual(wage_history_obj.get_ceiling(checkdate3), 149760)
