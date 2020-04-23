# Copyright (C) 2020 OdooERP România S.R.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from .common import TestHrEmployee
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import _


class TestHrMealVouchers(TestHrEmployee):

    def test_compute_name(self):
        first_day = datetime.strftime(
            datetime.today() + relativedelta(day=1), '%Y-%m-%d')
        last_day = datetime.strftime(
            datetime.today() + relativedelta(day=1, days=-1, months=1),
            '%Y-%m-%d'
        )
        meal_vouchers = self.env['hr.meal.vouchers'].create({
            'company_id': self.env.user.company_id.id,
            'date_from': first_day,
            'date_to': last_day
        })
        expected_name = _("%s - Period %s - %s") % (
            self.env.user.company_id.name, first_day, last_day)
        self.assertEqual(expected_name, meal_vouchers.name)

    def test_onchange_date_from(self):
        first_day = datetime.strftime(
            datetime.today() + relativedelta(day=1), '%Y-%m-%d')
        last_day = datetime.strftime(
            datetime.today() + relativedelta(day=1, days=-1, months=1),
            '%Y-%m-%d'
        )
        meal_vouchers = self.env['hr.meal.vouchers'].create({
            'company_id': self.env.user.company_id.id,
            'date_from': first_day,
            'date_to': last_day
        })
        new_first_day = datetime.strftime(
            datetime.today() + relativedelta(day=1, months=1), '%Y-%m-%d')
        new_last_day = datetime.strftime(
            datetime.today() + relativedelta(day=1, days=-1, months=2),
            '%Y-%m-%d'
        )
        meal_vouchers.date_from = new_first_day
        meal_vouchers._onchange_date_from()

        expected_name = _("%s - Period %s - %s") % (
            self.env.user.company_id.name, new_first_day, new_last_day)
        self.assertEqual(expected_name, meal_vouchers.name)
        self.assertEqual(meal_vouchers.date_to, new_last_day)

    def test_get_contracts(self):
        first_day = datetime.strftime(
            datetime.today() + relativedelta(day=1), '%Y-%m-%d')
        last_day = datetime.strftime(
            datetime.today() + relativedelta(day=1, days=-1, months=1),
            '%Y-%m-%d'
        )
        meal_vouchers = self.env['hr.meal.vouchers'].create({
            'company_id': self.env.user.company_id.id,
            'date_from': first_day,
            'date_to': last_day
        })

        self.env['res.company.meal.voucher'].create({
            'company_id': self.env.user.company_id.id,
            'date_from': first_day,
            'value': 10
        })

        contracts = meal_vouchers.get_contracts()
        init_contracts = len(contracts)

        contract_start_day = datetime.strftime(
            datetime.today() + relativedelta(months=-2), '%Y-%m-%d')

        contract_test3 = self.env['hr.contract'].create({
            'date_end': datetime.strftime(
                datetime.today(), '%Y-%m-%d'),
            'date_start': contract_start_day,
            'name': 'Contract for Test3',
            'wage': 3500.0,
            'state': 'open',
            'type_id': self.env.ref('hr_contract.hr_contract_type_emp').id,
            'employee_id': self.test_employee_2.id,
            'struct_id': self.env.ref('l10n_ro_hr_payroll.salarbaza').id,
            'resource_calendar_id': self.env.ref(
                'resource.resource_calendar_std'
            ).id
        })

        contract_test4 = self.env['hr.contract'].create({
            'date_end': datetime.strftime(
                datetime.today() + relativedelta(years=1), '%Y-%m-%d'),
            'date_start': contract_start_day,
            'name': 'Contract for Test4',
            'wage': 3200.0,
            'state': 'open',
            'type_id': self.env.ref('hr_contract.hr_contract_type_emp').id,
            'employee_id': self.test_employee_2.id,
            'struct_id': self.env.ref('l10n_ro_hr_payroll.salarbaza').id,
            'resource_calendar_id': self.env.ref(
                'resource.resource_calendar_std'
            ).id
        })

        contracts = meal_vouchers.get_contracts()
        self.assertEqual(len(contracts), init_contracts+2)
        self.assertIn(contract_test3, contracts)
        self.assertIn(contract_test4, contracts)

        self.assertIn(self.contract_test1, contracts)
        self.assertIn(self.contract_test2, contracts)

        meal_vouchers.build_lines()
        lines = meal_vouchers.line_ids
        contract1_line = lines.filtered(
            lambda l: l.contract_id == self.contract_test1
        )

        self.assertTrue(contract1_line)

        contract2_line = lines.filtered(
            lambda l: l.contract_id == self.contract_test2
        )
        self.assertTrue(contract2_line)

        contract3_line = lines.filtered(
            lambda l: l.contract_id == contract_test3
        )
        self.assertTrue(contract3_line)
        expected_days = self.env['hr.payslip'].get_worked_day_lines(
            contract_test3, first_day, last_day)
        self.assertTrue(contract3_line.vouchers_no, expected_days)
        self.assertEqual(contract3_line.voucher_value, 10)

        contract4_line = lines.filtered(
            lambda l: l.contract_id == contract_test4
        )
        self.assertTrue(contract4_line)
        expected_days = self.env['hr.payslip'].get_worked_day_lines(
            contract_test4, first_day, last_day
        )
        self.assertTrue(contract4_line.vouchers_no, expected_days)
        self.assertEqual(contract4_line.voucher_value, 10)
