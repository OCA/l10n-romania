# Copyright (C) 2020 OdooERP România S.R.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo.tests import common
from odoo.fields import Date


class TestHrEmployee(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestHrEmployee, cls).setUpClass()

        date_from = datetime.today() + relativedelta(day=1)

        # Configure a person related partner
        cls.test_person_related_1 = cls.env['res.partner'].create({
            'name': 'PersonRelated1',
        })

        # Configure 2 employees
        cls.test_employee_1 = cls.env['hr.employee'].create({
            'name': 'Test1',
            'gender': 'male',
            'birthday': '1974-05-01',
            'country_id': cls.env.ref('base.ro').id,
            'person_related': [(0, 0, {
                'partner_id': cls.test_person_related_1.id,
                'ssnid': 1900705380545,
                'relation_type': 'in_care',
                'relation': 'child'
            })]
        })
        cls.test_employee_2 = cls.env['hr.employee'].create({
            'name': 'Test2',
            'gender': 'female',
            'birthday': '1939-02-21',
            'country_id': cls.env.ref('base.ro').id
        })

        # Configure 2 contracts
        cls.contract_test1 = cls.env['hr.contract'].create({
            'date_end': Date.to_string((datetime.now() +
                                        timedelta(days=365))),
            'date_start': datetime.today().strftime('%Y-%m-01'),
            'name': 'Contract for Test1',
            'wage': 3500.0,
            'state': 'open',
            'type_id': cls.env.ref('hr_contract.hr_contract_type_emp').id,
            'employee_id': cls.test_employee_1.id,
            'struct_id': cls.env.ref('l10n_ro_hr_payroll.salarbaza').id,
            'resource_calendar_id': cls.env.ref(
                'resource.resource_calendar_std'
            ).id
        })
        cls.contract_test2 = cls.env['hr.contract'].create({
            'date_end': Date.to_string((datetime.now() +
                                        timedelta(days=365))),
            'date_start': Date.today(),
            'name': 'Contract for Test2',
            'wage': 3100.0,
            'state': 'open',
            'type_id': cls.env.ref('hr_contract.hr_contract_type_emp').id,
            'employee_id': cls.test_employee_2.id,
            'struct_id': cls.env.ref('l10n_ro_hr_payroll.salarbaza').id
        })

        # Configure 2 incomes
        cls.income01 = cls.env['hr.employee.income'].create({
            'number_of_days': 22,
            'number_of_hours': 176,
            'gross_amount': 3520.00,
            'net_amount': 1650.00,
            'date_from': datetime.strftime(
                datetime.today() + relativedelta(day=1, months=-1), '%Y-%m-%d'
            ),
            'date_to': datetime.strftime(
                datetime.today() + relativedelta(day=1, days=-1), '%Y-%m-%d',
            ),
            'employee_id': cls.test_employee_1.id
        })
        cls.income02 = cls.env['hr.employee.income'].create({
            'number_of_days': 22,
            'number_of_hours': 176,
            'gross_amount': 2640.00,
            'net_amount': 2300.00,
            'date_from': datetime.strftime(
                datetime.today() + relativedelta(day=1, months=-2), '%Y-%m-%d'
            ),
            'date_to': datetime.strftime(
                datetime.today() + relativedelta(day=1, months=-1, days=-1),
                '%Y-%m-%d',
            ),
            'employee_id': cls.test_employee_1.id
        })

        # Configure leave statuses
        cls.leave01 = cls.env['hr.holidays.status'].create({
            'name': 'Boala obisnuita',
            'color_name': 'violet',
            'limit': 1,
            'indemn_code': '1',
            'percentage': 75,
            'employer_days': 5,
            'max_days': 183,
            'is_sick_leave': True,
            'emergency': False,
            'timesheet_generate': False
        })

        # Configure diseases
        cls.disease1 = cls.env["hr.medical.disease"].create({
            'code': '1',
            'name': 'Holera'
        })

        # Configure work days
        first_work_day = 0
        for new_day in range(0, 3):
            new_date = date_from + relativedelta(days=new_day)
            if new_date.weekday() <= 5:
                first_work_day = new_date.day-1
                break

        # Configure leaves
        cls.initleave = cls.env['hr.holidays'].create(
            {'name': 'Med1',
             'holiday_status_id': cls.leave01.id,
             'date_from': (date_from +
                           relativedelta(days=first_work_day)).strftime(
                 '%Y-%m-%d 10:00:00'
             ),
             'date_to': (date_from +
                         relativedelta(days=first_work_day+7)).strftime(
                 '%Y-%m-%d 18:00:00'
             ),
             'type': 'remove',
             'employee_id': cls.test_employee_1.id,
             'disease_id': cls.disease1.id,
             'number_of_days_temp': 7
             })
        cls.initleave.action_validate()

        cls.leave = cls.env['hr.holidays'].create(
            {'name': 'Med2',
             'holiday_status_id': cls.leave01.id,
             'date_from': (date_from +
                           relativedelta(days=first_work_day+8)).strftime(
                 '%Y-%m-%d 10:00:00'
             ),
             'date_to': (date_from +
                         relativedelta(days=first_work_day+10)).strftime(
                 '%Y-%m-%d 18:00:00'
             ),
             'type': 'remove',
             'employee_id': cls.test_employee_1.id,
             'disease_id': cls.disease1.id,
             'initial_id': cls.initleave.id,
             'number_of_days_temp': 3
             })
        cls.leave.action_validate()
