# Copyright (C) 2014 Adrian Vasile
# Copyright (C) 2018 FOREST AND BIOMASS ROMANIA SA
# Copyright (C) 2020 OdooERP România S.R.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _


class HRMealVouchersLine(models.Model):
    _name = 'hr.meal.vouchers.line'
    _description = 'Meal Voucher per Employee'

    meal_voucher_id = fields.Many2one(
        'hr.meal.vouchers', 'Meal Voucher Run')
    employee_id = fields.Many2one('hr.employee', 'Employee')
    contract_id = fields.Many2one('hr.contract', 'Contract', index=True)
    vouchers_no = fields.Integer('# of Vouchers')
    voucher_value = fields.Float('Voucher Value')
    serial_from = fields.Char('Serial # from')
    serial_to = fields.Char('Serial # to')


class HRMealVouchers(models.Model):
    _name = 'hr.meal.vouchers'
    _description = 'Meal Vouchers per Company'

    @api.depends('company_id', 'date_from', 'date_to')
    def _compute_name(self):
        for res in self:
            res.name = _("%s - Period %s - %s") % (
                res.company_id.name, res.date_from, res.date_to)

    @api.onchange('date_from')
    def _onchange_date_from(self):
        date_from = fields.Date.from_string(self.date_from)
        self.date_to = datetime(
            date_from.year, date_from.month,
            1)+relativedelta(months=1, days=-1)

    name = fields.Char(compute="_compute_name", string='Name', readonly=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.user.company_id)
    date_from = fields.Date(
        'Date From', required=True,
        default=time.strftime('%Y-%m-01'))
    date_to = fields.Date('Date To', required=True)
    line_ids = fields.One2many('hr.meal.vouchers.line', 'meal_voucher_id')

    def get_contracts(self):
        employees = self.env['hr.employee'].search([
            ('active', '=', True),
            ('company_id', '=', self.company_id.id),
            ('company_id.meal_voucher_ids', '!=', False)
        ])
        # To Do: Suspended Contracts
        clause = [('employee_id', 'in', employees.ids), '|', '|']
        clause += ['&', ('date_end', '<=', self.date_to),
                   ('date_end', '>=', self.date_from)]
        # OR if it starts between the given dates
        clause += ['&', ('date_start', '<=', self.date_to),
                   ('date_start', '>=', self.date_from)]
        # OR if it starts before the date_from and finish
        # after the date_end (or never finish)
        clause += ['&', ('date_start', '<=', self.date_from),
                   '|', ('date_end', '=', False),
                   ('date_end', '>=', self.date_to)]
        return self.env['hr.contract'].search(clause)

    @api.multi
    def build_lines(self):
        self.ensure_one()
        lines_obj = self.env['hr.meal.vouchers.line']
        contracts = self.get_contracts()
        self.line_ids.unlink()
        voucher_value = self.company_id.get_meal_voucher_value(self.date_from)
        for contract in contracts:
            tich_rule = self.env.ref('l10n_ro_hr_payroll.tichetedemasa')
            if tich_rule and tich_rule in contract.struct_id.rule_ids:
                num = self.env['hr.payslip'].get_worked_day_lines(
                    contract, self.date_from, self.date_to
                )[0]['number_of_days']

                if num > 0.0:
                    lines_obj.create({
                        'meal_voucher_id': self.id,
                        'employee_id': contract.employee_id.id,
                        'contract_id': contract.id,
                        'vouchers_no': num,
                        'voucher_value': voucher_value
                    })
        return True
