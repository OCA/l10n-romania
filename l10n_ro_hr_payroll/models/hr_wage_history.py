# Copyright (C) 2014 Adrian Vasile
# Copyright (C) 2018 FOREST AND BIOMASS ROMANIA SA
# Copyright (C) 2020 OdooERP România S.R.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class HRWageHistory(models.Model):
    _name = 'hr.wage.history'
    _description = 'Wage History of Minimum and Medium Salary'
    _rec_name = 'date'
    _order = 'date desc'
    _sql_constrains = [(
        'date_uniq',
        'unique (date)',
        'Unique date',
    )]

    date = fields.Date('Month/Year', required=True, index=True)
    min_wage = fields.Integer('Minimum Wage per economy', required=True)
    med_wage = fields.Integer('Medium Wage per economy', required=True)
    working_days = fields.Integer(
        'Number of Working(ed) Days', required=True)
    ceiling_min_wage = fields.Integer(
        'Ceiling for 6 month income', required=True)

    @api.model
    def get_medium_wage(self, checkdate):
        res = self.search([('date', '<=', checkdate)])
        if res:
            return res[0].med_wage
        return 0.00

    @api.model
    def get_minimum_wage(self, checkdate):
        res = self.search([('date', '<=', checkdate)])
        if res:
            return res[0].min_wage
        return 0.00

    @api.model
    def get_ceiling(self, checkdate):
        res = self.search([('date', '<=', checkdate)])
        if res:
            return res[0].ceiling_min_wage
        return 0.00
