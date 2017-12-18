# Copyright (C) 2014 Adrian Vasile
# Copyright (C) 2017 FOREST AND BIOMASS ROMANIA SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime, timedelta
from odoo import api, fields, models, _


class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    daily_base = fields.Float(_('Daily Base'))
    employer_days = fields.Integer(_('# Days by Employer'))
    budget_days = fields.Integer(_('# Days by Social Security'))
    employer_amount = fields.Float(_('Amount by Employer'))
    budget_amount = fields.Float(_('Amount by Social Sevcurity'))
    total_amount = fields.Float(_('Total Amount'))


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contract_ids: list of contract id
        @return: returns a list of dict containing the input that should be
                 applied for the given contract between date_from and date_to
        """
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

        res = []
        for contract in contracts:
            attendances = {
                'name': _("Normal Working Days paid at 100%"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': 0.0,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            }
            leaves = {}
            day_from = datetime.strptime(date_from, "%Y-%m-%d")
            day_to = datetime.strptime(date_to, "%Y-%m-%d")
            nb_of_days = (day_to - day_from).days + 1
            for day in range(0, nb_of_days):
                working_hours_on_day = \
                    contract.employee_id.get_day_work_hours_count(
                        day_from + timedelta(days=day),
                        calendar=contract.resource_calendar_id)
                if working_hours_on_day:
                    # the employee had to work
                    emp_leaves = was_on_leave(contract.employee_id.id,
                                              day_from + timedelta(days=day))
                    if emp_leaves:
                        # if he was on leave, fill the leaves dict
                        for leave in emp_leaves:
                            if leave.holiday_status_id.leave_code:
                                leave_code = leave.holiday_status_id.leave_code
                            else:
                                leave_code = leave.holiday_status_id.name
                            if leave_code in leaves:
                                leaves[leave_code]['number_of_days'] += 1.0
                                leaves[leave_code]['number_of_hours'] +=\
                                    working_hours_on_day
                                newday = day_from + timedelta(days=day)
                                if newday == fields.Date.from_string(
                                        leave.date_from):
                                    leaves[leave_code]['employer_days'] +=\
                                        leave.employer_days
                                    leaves[leave_code]['budget_days'] +=\
                                        leave.budget_days
                                    leaves[leave_code]['employer_amount'] +=\
                                        leave.employer_amount
                                    leaves[leave_code]['budget_amount'] +=\
                                        leave.budget_amount
                                    leaves[leave_code]['total_amount'] +=\
                                        leave.total_amount
                            else:
                                leaves[leave_code] = {
                                    'name': leave.holiday_status_id.name,
                                    'sequence': 5,
                                    'code': leave_code,
                                    'number_of_days': 1.0,
                                    'number_of_hours': working_hours_on_day,
                                    'contract_id': contract.id,
                                    'daily_base': leave.daily_base,
                                    'employer_days': leave.employer_days,
                                    'budget_days': leave.budget_days,
                                    'employer_amount': leave.employer_amount,
                                    'budget_amount': leave.budget_amount,
                                    'total_amount': leave.total_amount,
                                }
                    else:
                        # add the input vals to tmp (increment if existing)
                        attendances['number_of_days'] += 1.0
                        attendances['number_of_hours'] += working_hours_on_day
            leaves = [value for key, value in leaves.items()]
            res += [attendances] + leaves
        return res

    @api.one
    @api.depends('worked_days_line_ids')
    def _get_working_days(self):
        self.working_days = sum(
            line.number_of_days for line in self.worked_days_line_ids)

    working_days = fields.Integer('# Working Days',
                                  compute='_get_working_days',
                                  store=True)
