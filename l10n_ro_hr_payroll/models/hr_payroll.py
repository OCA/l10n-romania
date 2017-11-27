# Copyright (C) 2014 Adrian Vasile
# Copyright (C) 2018 FOREST AND BIOMASS ROMANIA SA
# Copyright (C) 2020 OdooERP România S.R.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    daily_base = fields.Float('Daily Base')
    employer_days = fields.Integer('# Days by Employer')
    budget_days = fields.Integer('# Days by Social Security')
    employer_amount = fields.Float('Amount by Employer')
    budget_amount = fields.Float('Amount by Social Security')
    total_amount = fields.Float('Total Amount')


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
            contract_start_day = datetime.strptime(contract.date_start, "%Y-%m-%d")
            contract_end_day = False
            if contract.date_end:
                contract_end_day = datetime.strptime(contract.date_end, "%Y-%m-%d")
            nb_of_days = (day_to - day_from).days + 1
            for day in range(0, nb_of_days):
                check_active = False
                date_check = day_from + timedelta(days=day)
                if contract_end_day and date_check <= contract_end_day:
                    check_active = True
                if not contract_end_day and date_check >= contract_start_day:
                    check_active = True
                working_hours_on_day = \
                    contract.employee_id.get_day_work_hours_count(
                        day_from + timedelta(days=day),
                        calendar=contract.resource_calendar_id)
                if working_hours_on_day and check_active:
                    # the employee had to work
                    emp_leaves = was_on_leave(contract.employee_id.id,
                                              day_from + timedelta(days=day))
                    if emp_leaves:
                        # if he was on leave, fill the leaves dict
                        for leave in emp_leaves:
                            if leave.holiday_status_id.leave_code:
                                leave_code = \
                                    leave.holiday_status_id.leave_code
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

    @api.multi
    @api.depends('worked_days_line_ids')
    def _compute_working_days(self):
        self.ensure_one()
        date_from = \
            datetime.strptime(self.date_from, "%Y-%m-%d") + relativedelta(day=1)
        last_day = \
            datetime.strptime(self.date_from, "%Y-%m-%d") + relativedelta(day=1, months=1, days=-1)

        nb_of_days = last_day.day

        total = 0
        for day in range(0, nb_of_days):
            total_day = date_from + \
                        relativedelta(days=day)
            if total_day.weekday() < 5:
                total += 1
        self.working_days = total

    working_days = fields.Integer('# Working Days',
                                  compute='_compute_working_days',
                                  store=True)

    @api.model
    def get_contract(self, employee, date_from, date_to):
        """
        @param employee: recordset of employee
        @param date_from: date field
        @param date_to: date field
        @return: returns the ids of all the contracts for the given employee that need to be considered for the given dates
        """
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', employee.id), ('state', 'not in', ['draft', 'cancelled']), '|', '|'] + clause_1 + clause_2 + clause_3
        return self.env['hr.contract'].search(clause_final).ids
