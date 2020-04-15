# Copyright (C) 2020 OdooERP România S.R.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from .common import TestHrEmployee
from datetime import datetime


class TestHrPayrollPayslipsByEmployees(TestHrEmployee):
    def test_compute_sheet(self):
        contract2 = self.contract_test1.copy()
        self.contract_test1.write({
            'date_end': datetime.today().strftime('%Y-%m-10'),
            'state': 'close'
        })

        contract2.write({
            'date_start': datetime.today().strftime('%Y-%m-15'),
            'state': 'open'
        })

        payslips = self.env['hr.payslip'].search([
            ('employee_id', '=', self.test_employee_1.id)
        ])
        self.assertFalse(payslips)

        payslip_run = self.env['hr.payslip.run'].create({
            'date_start': datetime.today().strftime('%Y-%m-01'),
            'date_end': datetime.today().strftime('%Y-%m-25'),
            'name': 'Test Payslip Batch'
        })

        payslip_employees = self.env['hr.payslip.employees'].create({
            'employee_ids': [(6, 0, self.test_employee_1.ids)]
        })

        payslip_employees.with_context(active_id=payslip_run.id).compute_sheet()

        payslips = self.env['hr.payslip'].search([
            ('employee_id', '=', self.test_employee_1.id)
        ])
        self.assertEqual(len(payslips), 2)

        payslip1 = payslips[0]
        self.assertEqual(payslip1.date_to, datetime.today().strftime('%Y-%m-10'))
        self.assertEqual(payslip1.contract_id, self.contract_test1)

        payslip2 = payslips[1]
        self.assertEqual(payslip2.date_from, datetime.today().strftime('%Y-%m-15'))
        self.assertEqual(payslip2.contract_id, contract2)
