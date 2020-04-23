# Copyright (C) 2014 Adrian Vasile
# Copyright (C) 2018 FOREST AND BIOMASS ROMANIA SA
# Copyright (C) 2020 OdooERP România S.R.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time
from odoo import api, fields, models


class ResCompanyMealVoucher(models.Model):
    _name = 'res.company.meal.voucher'
    _description = 'Meal Vouchers Value'
    _order = 'company_id, date_from desc'

    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.user.company_id)
    date_from = fields.Date(
        'Date From', required=True,
        default=time.strftime('%Y-%m-01'),
        help='Date should be start day of month.')
    value = fields.Float('Meal Voucher Value')


class ResCompany(models.Model):
    _inherit = 'res.company'

    meal_voucher_ids = fields.One2many(
        'res.company.meal.voucher', 'company_id',
        string='Meal Voucher Values')

    @api.model
    def get_meal_voucher_value(self, date=False):
        if not date:
            date = fields.Date.today()
        res = self.meal_voucher_ids.filtered(
            lambda record: record.date_from <= date)
        return res[0].value if res else 0.00

    @api.model
    def get_medium_wage(self, date=False):
        if not date:
            date = fields.Date.today()
        return self.env['hr.wage.history'].get_medium_wage(date)

    @api.model
    def get_minimum_wage(self, date=False):
        if not date:
            date = fields.Date.today()
        return self.env['hr.wage.history'].get_minimum_wage(date)

    @api.model
    def get_ceiling(self, date=False):
        if not date:
            date = fields.Date.today()
        return self.env['hr.wage.history'].get_ceiling(date)
