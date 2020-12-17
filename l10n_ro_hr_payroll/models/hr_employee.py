# Copyright (C) 2014 Adrian Vasile
# Copyright (C) 2017 FOREST AND BIOMASS ROMANIA SA
# Copyright (C) 2020 OdooERP România S.R.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class HREmployeeIncome(models.Model):
    _name = 'hr.employee.income'
    _description = 'Employee income from payslips'

    @api.onchange('payslip_id')
    def _onchange_payslip_id(self):
        days = hours = gross = net = 0.00
        date_from = date_to = False
        if self.payslip_id:
            date_from = self.payslip_id.date_from
            date_to = self.payslip_id.date_to
            worked_days = self.payslip_id.worked_days_line_ids
            if worked_days:
                days = sum(line.number_of_days for line in worked_days)
                hours = sum(line.number_of_hours for line in worked_days)
            gross_id = self.env.ref('l10n_ro_hr_payroll.venit_brut')
            if gross_id:
                gross_line_id = self.env['hr.payslip.line'].search(
                    [('slip_id', '=', self.payslip_id.id),
                     ('salary_rule_id', '=', gross_id[0].id)])
                if gross_line_id:
                    gross = gross_line_id[0].total
            net_id = self.env.ref('l10n_ro_hr_payroll.salarnet')
            if net_id:
                net_line_id = self.env['hr.payslip.line'].search(
                    [('slip_id', '=', self.payslip_id.id),
                     ('salary_rule_id', '=', net_id[0].id)])
                if net_line_id:
                    net = net_line_id[0].total

                    self.number_of_days = days
                    self.number_of_hours = hours
                    self.gross_amount = gross
                    self.net_amount = net
                    self.date_from = date_from
                    self.date_to = date_to

    employee_id = fields.Many2one('hr.employee', 'Employee',
                                  required=True, index=True)
    payslip_id = fields.Many2one('hr.payslip', 'Payslip')
    date_from = fields.Date('Date From', required=True)
    date_to = fields.Date('Date To', required=True)
    number_of_days = fields.Integer('Number of Days', required=True)
    number_of_hours = fields.Integer('Number of Hours', required=True)
    gross_amount = fields.Float('Gross Income', required=True)
    net_amount = fields.Float('Net Salary', required=True)


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    income_ids = fields.One2many('hr.employee.income', 'employee_id',
                                 'Payslip History')

    @api.multi
    def _get_holiday_base(self, date=False, month_no=False):
        self.ensure_one()
        if not date:
            date = fields.Date.today()
        if isinstance(date, str):
            date = fields.Date.from_string(date)
        date = date + relativedelta(day=1)
        date_string = fields.Date.to_string(date)
        if not month_no:
            month_no = 6
        prev_date = date + relativedelta(months=(-1) * month_no)
        prev_date_string = fields.Date.to_string(prev_date)
        income_ids = self.income_ids.filtered(
            lambda income: income.date_to <= date_string and
            income.date_from >= prev_date_string)
        days = gross = False
        if income_ids:
            gross = sum(income.gross_amount for income in income_ids)
            days = sum(income.number_of_days for income in income_ids)
        else:
            gross = self.contract_id.wage
            days = self.env['hr.wage.history'].search(
                [('date', '=', date)]).working_days
        if gross and days and days != 0.00:
            return gross / days
        return 0
