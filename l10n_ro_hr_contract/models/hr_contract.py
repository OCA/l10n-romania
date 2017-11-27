# Copyright (C) 2017 FOREST AND BIOMASS ROMANIA SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class HRInsuranceType(models.Model):
    _name = 'hr.insurance.type'
    _description = "Employee insurance type"

    @api.model
    def _get_insurance_type(self):
        return [('1', 'A-B'), ('2', 'C')]

    type = fields.Selection('_get_insurance_type',
                            string='Type', help='Insurance type')
    code = fields.Char('Code', required=True, help='Insurance code')
    name = fields.Char('Name', required=True, help='Insurance name')


class hr_contract(models.Model):
    _inherit = 'hr.contract'

    @api.model
    def _get_work_norm(self):
        work = [('N', 'cu norma intreaga'),
                ('P1', 'cu timp de lucru partial de 1 ora'),
                ('P2', 'cu timp de lucru partial de 2 ore'),
                ('P3', 'cu timp de lucru partial de 3 ore'),
                ('P4', 'cu timp de lucru partial de 4 ore'),
                ('P5', 'cu timp de lucru partial de 5 ore'),
                ('P6', 'cu timp de lucru partial de 6 ore'),
                ('P7', 'cu timp de lucru partial de 7 ore')]
        return work

    @api.model
    def _get_work_hours(self):
        hours = [('6', '6 ore'), ('7', '7 ore'), ('8', '8 ore')]
        return hours

    @api.model
    def _get_work_type(self):
        worktype = [('1', 'Conditii normale'),
                    ('2', 'Conditii deosebite'),
                    ('3', 'Conditii Speciale')]
        return worktype

    @api.model
    def _get_work_special(self):
        workspecial = [
            ('0', 'Rest'),
            ('1', 'art.30 alin.(1) lit.a) din L263/2010'),
            ('2', 'art.30 alin.(1) lit.b) din L263/2010 zona I radiatii'),
            ('3', 'art.30 alin.(1) lit.b) din L263/2010 zona II radiatii'),
            ('4', 'art.30 alin.(1) lit.c) din L263/2010 (Militari)'),
            ('5', 'art.30 alin.(1) lit.d) din L263/2010 (Aviatori)'),
            ('6', 'art.30 alin.(1) lit.e) din L263/2010/'
                  '(cf anexa 2,3 din L263)'),
            ('7', 'art.30 alin.(1) lit.f )din L263/2010 (Artisti)')]
        return workspecial

    revisal_no = fields.Char('REVISAL Number', required=True,
                             help='Numbered registered in Revisal')
    internal_no = fields.Char('Internal Number',
                              help='Internal Number')
    period_type = fields.Boolean(
        'Determined Period', help="The contract period type")
    suspended = fields.Boolean('Contract suspended?')
    sus_date_from = fields.Date('Suspended from')
    sus_date_to = fields.Date('Suspended to')
    pensioneer = fields.Boolean(
        'Pensioneer', help="Is the employee a pensioneer")
    tax_exempt = fields.Boolean('Tax Exempt', help="Exempt from income tax")
    work_norm = fields.Selection(
        '_get_work_norm', string='Work Norm', required=True,
        help="The type of work depending on worked hours")
    work_hour = fields.Selection(
        '_get_work_hours', string='Hour per day', required=True,
        help="The numbers of hours/day")
    work_type = fields.Selection(
        '_get_work_type', string='Work type', required=True,
        help="The work type based on conditions")
    insurance_type = fields.Many2one(
        'hr.insurance.type', string='Insurance type',
        required=True, help="Insurance type")
    work_special = fields.Selection(
        '_get_work_special', string='Special Conditions',
        help="Special condition of work")
    sign_date = fields.Date(
        'Date', required=True, help="Date of signing the contract")
