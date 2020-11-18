# Copyright (C) 2014 Adrian Vasile
# Copyright (C) 2018 FOREST AND BIOMASS ROMANIA SA
# Copyright (C) 2020 OdooERP România S.R.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime, timedelta
from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta


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

    def change_in_hour(self, hour_from, hour_to):
        diff = hour_to - hour_from
        minutes = (diff.seconds + diff.microseconds / 1000000.0) / 60
        hours = minutes / 60
        minutes -= hours * 60
        res = (hours + minutes / 60)
        return res

    def overtime(self, hour_from, hour_to, hfrom, hto):
        ore_suplimentare = 0
        if hour_from.hour >= hfrom.hour:
            if hour_from.hour < hto.hour:
                if hour_to.hour >= hto.hour and hour_to.hour < 22:
                    ore_suplimentare += self.change_in_hour(hto, hour_to)
                if hour_to.hour >= hto.hour and hour_to.hour > 22:
                    nh = hour_to.replace(hour=22, minute=00)
                    ore_suplimentare += self.change_in_hour(hto, nh)
                if hour_to.hour >= 6 and hour_to.hour < hfrom.hour:
                    nh1 = hour_from.replace(hour=22, minute=00)
                    nh12 = hour_to.replace(hour=6, minute=00)
                    ore_suplimentare += self.change_in_hour(hto, nh1)
                    ore_suplimentare += self.change_in_hour(nh12, hour_to)
                if hour_to.hour >= hfrom.hour and hour_to.hour < hto.hour:
                    nh1 = hour_from.replace(hour=22, minute=00)
                    nh12 = hour_to.replace(hour=6, minute=00)
                    ore_suplimentare += self.change_in_hour(hto, nh1)
                    ore_suplimentare += self.change_in_hour(nh12, hto)
                if hour_to.hour < 6:
                    nh1 = hour_from.replace(hour=22, minute=00)
                    ore_suplimentare += self.change_in_hour(hto, nh1)
            if hour_from.hour >= hto.hour:
                if hour_from.hour < 22 and hour_to.hour >= 22:
                    nh1 = hour_from.replace(hour=22, minute=00)
                    ore_suplimentare += self.change_in_hour(hour_from, nh1)
                if hour_from.hour < 22 and hour_to.hour < 6:
                    nh1 = hour_from.replace(hour=22, minute=00)
                    ore_suplimentare += self.change_in_hour(hour_from, nh1)
                if hour_from.hour < 22 and hour_to.hour <= hfrom.hour and \
                        hour_to.hour > 6:
                    nh1 = hour_from.replace(hour=22, minute=00)
                    nh12 = hour_to.replace(hour=6, minute=00)
                    ore_suplimentare += self.change_in_hour(hour_from, nh1)
                    ore_suplimentare += self.change_in_hour(nh12, hour_to)
                if hour_from.hour >= 22 and hour_to.hour <= hfrom.hour and \
                        hour_to.hour > 6:
                    nh12 = hour_to.replace(hour=6, minute=00)
                    ore_suplimentare += self.change_in_hour(nh12, hour_to)
        if hour_from.hour < hfrom.hour:
            if hour_from.hour < 6:
                if hour_to.hour > 6 and hour_to.hour <= hfrom.hour:
                    nh1 = hour_from.replace(hour=6, minute=00)
                    ore_suplimentare += self.change_in_hour(nh1, hour_to)
                if hour_to.hour > hfrom.hour and hour_to.hour <= hto.hour:
                    nh1 = hour_to.replace(hour=6, minute=00)
                    ore_suplimentare += self.change_in_hour(nh1, hfrom)
                if hour_to.hour > hto.hour and hour_to.hour < 22:
                    nh1 = hour_from.replace(hour=6, minute=00)
                    ore_suplimentare += self.change_in_hour(nh1, hfrom)
                    ore_suplimentare += self.change_in_hour(hto, hour_to)
                if hour_to.hour >= 22:
                    nh1 = hour_from.replace(hour=22, minute=00)
                    nh12 = hour_to.replace(hour=6, minute=00)
                    ore_suplimentare += self.change_in_hour(hto, nh1)
                    ore_suplimentare += self.change_in_hour(nh12, hfrom)
            if hour_from.hour >= 6:
                if hour_to.hour > 6 and hour_to.hour <= hfrom.hour:
                    ore_suplimentare += self.change_in_hour(hour_to, hour_from)
                if hour_to.hour > hfrom.hour and hour_to.hour <= hto.hour:
                    ore_suplimentare += self.change_in_hour(hour_from, hfrom)
                if hour_to.hour > hto.hour and hour_to.hour < 22:
                    ore_suplimentare += self.change_in_hour(hour_from, hfrom)
                    ore_suplimentare += self.change_in_hour(hto, hour_to)
                if hour_to.hour >= 22:
                    nh1 = hour_from.replace(hour=22, minute=00)
                    ore_suplimentare += self.change_in_hour(hour_from, hfrom)
                    ore_suplimentare += self.change_in_hour(hto, nh1)
        return ore_suplimentare

    def night_hours(self, hour_from, hour_to):
        hour_night = 0
        dif = self.change_in_hour(hour_from, hour_to)
        if hour_from.hour >= 22:
            if hour_to.hour < 6:
                hour_night += self.change_in_hour(hour_from, hour_to)
            if hour_to.hour >= 6 and hour_to.hour < 22:
                nh1 = hour_to.replace(hour=6, minute=00)
                hour_night += self.change_in_hour(hour_from, nh1)
            if hour_to.hour > 22 and hour_to.hour <= 24:
                hour_night += self.change_in_hour(hour_from, hour_to)
        else:
            if hour_from.hour <= 6 and hour_to.hour <= 6:
                hour_night += self.change_in_hour(hour_from, hour_to)
            if hour_from.hour >= 6 and hour_to.hour <= 6:
                nh1 = hour_from.replace(hour=22, minute=00)
                hour_night += self.change_in_hour(nh1, hour_to)
            if hour_from.hour >= 6 and hour_to.hour >= 22:
                nh1 = hour_from.replace(hour=22, minute=00)
                hour_night += self.change_in_hour(nh1, hour_to)
            if hour_from.hour >= 6 and hour_to.hour <= 22 and dif > 19:
                nh1 = hour_from.replace(hour=22, minute=00)
                nh12 = hour_to.replace(hour=6, minute=00)
                hour_night += self.change_in_hour(nh1, nh12)
        return hour_night

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
            night = {
                'name': _("Night Working Days"),
                'sequence': 10,
                'code': 'NIGHT',
                'number_of_days': 0.00,
                'number_of_hours': 0.00,
                'contract_id': contract.id,
            }
            weekend = {
                'name': _("Weekend Working Days"),
                'sequence': 11,
                'code': 'WEEKEND',
                'number_of_days': 0.00,
                'number_of_hours': 0.00,
                'contract_id': contract.id,
            }
            holiday = {
                'name': _("Holiday Working Days"),
                'sequence': 12,
                'code': 'HOLIDAY',
                'number_of_days': 0.00,
                'number_of_hours': 0.00,
                'contract_id': contract.id,
            }
            suplimentar = {
                'name': _("Ore Suplimentare"),
                'sequence': 13,
                'code': 'SUPL',
                'number_of_days': 0.00,
                'number_of_hours': 0.00,
                'contract_id': contract.id,
            }
            leaves = {}
            day_from = datetime.strptime(date_from, "%Y-%m-%d")
            day_to = datetime.strptime(date_to, "%Y-%m-%d")
            contract_start_day = datetime.strptime(contract.date_start,
                                                   "%Y-%m-%d")
            contract_end_day = False

            if contract.date_end:
                contract_end_day = datetime.strptime(contract.date_end,
                                                     "%Y-%m-%d")
            nb_of_days = (day_to - day_from).days + 1
            check_active = False
            for day in range(0, nb_of_days):
                date_check = day_from + timedelta(days=day)
                if contract_end_day and date_check <= contract_end_day:
                    check_active = True
                if not contract_end_day and date_check >= contract_start_day:
                    check_active = True
            for day in range(0, nb_of_days):
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
                                if newday.date() == fields.Date.from_string(
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
                        dd = day_from + timedelta(days=day)
                        public_holiday = \
                            self.env['hr.holidays.public.line'].search(
                                [('date', '=', dd.date())])
                        if public_holiday:
                            attendances['number_of_days'] += 0.0
                            attendances['number_of_hours'] += 0.0
                        else:
                            attendances['number_of_days'] += 1.0
                            attendances['number_of_hours'] += working_hours_on_day

            attendance = self.env['hr.attendance'].search([
                ('check_in', '>=', date_from),
                ('check_out', '<=', date_to),
                ('employee_id', '=', contract.employee_id.id)])
            hour_night = 0.00
            hour_isweekend = 0.00
            hour_holiday = 0.00
            ore_suplimentare = 0.00
            resource_calendar_id = contract.resource_calendar_id
            for att in attendance:
                check_in = datetime.strptime(att.check_in, '%Y-%m-%d %H:%M:%S')
                check_out = datetime.strptime(att.check_out, '%Y-%m-%d %H:%M:%S')
                hour_from = fields.Datetime.context_timestamp(
                    self.with_context(tz=att.employee_id.user_id.tz), check_in)
                hour_to = fields.Datetime.context_timestamp(
                    self.with_context(tz=att.employee_id.user_id.tz), check_out)
                if resource_calendar_id:
                    resource_attendance = \
                        self.env['resource.calendar.attendance'].search(
                            [('calendar_id', '=', resource_calendar_id.id),
                             ('dayofweek', '=', hour_from.weekday())])
                    if resource_attendance:
                        hfrom = hour_from.replace(
                            hour=int(resource_attendance[0].hour_from),
                            minute=0)
                        hto = hour_from.replace(
                            hour=int(resource_attendance[-1].hour_to),
                            minute=0)
                    else:
                        hfrom = hour_from.replace(hour=8, minute=0)
                        hto = hour_from.replace(hour=17, minute=0)
                public_holiday = self.env['hr.holidays.public.line'].search(
                    [('date', '=', hour_from.date())])
                if hour_from.isoweekday() <= 5 and not public_holiday:
                    ore_suplimentare += self.overtime(hour_from, hour_to, hfrom, hto)

                hour_night += self.night_hours(hour_from, hour_to)

                if hour_from.isoweekday() > 5 and not public_holiday:
                    hour_isweekend += self.change_in_hour(hour_from, hour_to)

                if public_holiday:
                    hour_holiday += self.change_in_hour(hour_from, hour_to)

            if hour_night != 0.00:
                night = {
                    'name': 'Night Working Days',
                    'sequence': 10,
                    'code': 'NIGHT',
                    'number_of_days': 0.00,
                    'number_of_hours': hour_night,
                    'contract_id': contract.id,
                }
            if hour_isweekend != 0.00:
                weekend = {
                    'name': 'Weekend Working Days',
                    'sequence': 11,
                    'code': 'WEEKEND',
                    'number_of_days': 0.00,
                    'number_of_hours': hour_isweekend,
                    'contract_id': contract.id,
                }
            if hour_holiday != 0.00:
                holiday = {
                    'name': 'Holiday Working Days',
                    'sequence': 12,
                    'code': 'HOLIDAY',
                    'number_of_days': 0.00,
                    'number_of_hours': hour_holiday,
                    'contract_id': contract.id,
                }
            if ore_suplimentare != 0.00:
                suplimentar = {
                    'name': _("Ore Suplimentare"),
                    'sequence': 13,
                    'code': 'SUPL',
                    'number_of_days': 0.00,
                    'number_of_hours': ore_suplimentare,
                    'contract_id': contract.id,
                }
            leaves = [value for key, value in leaves.items()]
            res += [attendances] + leaves + [night] + \
                   [weekend] + [holiday] + [suplimentar]
        return res

    @api.multi
    @api.depends('worked_days_line_ids')
    def _compute_working_days(self):
        self.ensure_one()
        date_from = \
            datetime.strptime(self.date_from, "%Y-%m-%d") + \
            relativedelta(day=1)
        last_day = \
            datetime.strptime(self.date_from, "%Y-%m-%d") + \
            relativedelta(day=1, months=1, days=-1)

        nb_of_days = last_day.day
        public_holiday = self.env['hr.holidays.public.line'].search(
            [('date', '>=', date_from), ('date', '<=', last_day)])
        holiday = 0
        for day in public_holiday:
            day = fields.Date.from_string(day.date)
            if day.weekday() < 5:
                holiday += 1

        total = 0
        for day in range(0, nb_of_days):
            total_day = date_from + \
                relativedelta(days=day)
            if total_day.weekday() < 5:
                total += 1
        self.working_days = total - holiday

    working_days = fields.Integer('# Working Days',
                                  compute='_compute_working_days',
                                  store=True)

    @api.model
    def get_contract(self, employee, date_from, date_to):
        """
        @param employee: recordset of employee
        @param date_from: date field
        @param date_to: date field
        @return: returns the ids of all the contracts for the given employee
        that need to be considered for the given dates
        """
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to),
                    ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to),
                    ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after
        # the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|',
                    ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', employee.id),
                        ('state', 'not in',
                         ['draft', 'cancelled']), '|', '|'] + \
            clause_1 + clause_2 + clause_3
        return self.env['hr.contract'].search(clause_final).ids

    def action_payslip_done(self):
        res = super(HrPayslip, self).action_payslip_done()
        income_obj = self.env['hr.employee.income']
        for payslip in self:
            if payslip.state == 'done':
                income = income_obj.create({
                    'employee_id': payslip.employee_id.id,
                    'payslip_id': payslip.id,
                    'date_from': payslip.date_from,
                    'date_to': payslip.date_to,
                    'number_of_days': 0,
                    'number_of_hours': 0,
                    'gross_amount': 0,
                    'net_amount': 0
                })
                income._onchange_payslip_id()
        return res
