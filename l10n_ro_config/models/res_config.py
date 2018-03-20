# Copyright (C) 2015 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import os
from odoo import models, fields, api, tools


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_l10n_ro_siruta = fields.Boolean(
        'Romanian SIRUTA',
        help='This allows you to manage the Romanian Zones, States, Communes: '
             '\n The address fields will contain city, commune, state, zone, '
             'country, zip.')
    module_l10n_ro_partner_unique = fields.Boolean(
        'Partners unique by VAT, NRC',
        help='This allows you to have unique partners by VAT and NRC. '
             'per company.')
    module_l10n_ro_partner_create_by_vat = fields.Boolean(
        'Romania - Partner Create by VAT',
        help='This allows you to create partners by VAT based on '
             'ANAF webservice.')
    module_l10n_ro_hr = fields.Boolean(
        'Romania - Human Resources',
        help='This allows you to manage related persons on employees, '
             'insurance and company risk rates based on CAEN.')
    module_l10n_ro_hr_contract = fields.Boolean(
        'Romania - Employee Contracts',
        help='This allows you to manage employees contracts, '
             'based on Romanian legislation.')
    module_l10n_ro_hr_medical_holidays = fields.Boolean(
        'Romania - Medical Leaves',
        help='This allows you to input sick leaves based on '
             'Romanian legislation.')
    module_l10n_ro_hr_payroll = fields.Boolean(
        'Romania - Payroll',
        help='This alows you to manage salary rules, meal vouchers, '
             'wage history for minimun and medium salary .')
    module_l10n_ro_hr_payroll_account = fields.Boolean(
        'Romania - Payroll Accounting',
        help='This adds account on salary ruled defined in l10n_ro_payroll.')
    siruta_update = fields.Boolean('Load / Update Siruta Data')
    hr_job_update = fields.Boolean('Load / Update HR Job Data')
    caen_update = fields.Boolean('Load / Update Company CAEN Data')
    medical_update = fields.Boolean('Load / Update Medical Leaves Data')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(siruta_update=False, hr_job_update=False,
                   caen_update=False, medical_update=False)
        return res

    @api.multi
    def execute(self):
        self.ensure_one()
        res = super(ResConfigSettings, self).execute()
        data_dir = os.path.join(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))), 'examples')
        # Load SIRUTA datas if field is checked
        if self.siruta_update:
            # First check if module is installed
            installed = self.env['ir.module.module'].search(
                [('name', '=', 'l10n_ro_siruta'),
                 ('state', '=', 'installed')])
            if installed:
                path = data_dir + '/l10n_ro_siruta/'
                files = ['res.country.zone.csv',
                         'res.country.state.csv',
                         'res.country.commune.csv',
                         'res.city.csv']
                for file1 in files:
                    with tools.file_open(path + file1) as fdata:
                        tools.convert_csv_import(self._cr,
                                                 'l10n_ro_config',
                                                 file1,
                                                 bytes(fdata.read(), 'utf-8'),
                                                 {},
                                                 mode="init",
                                                 noupdate=True)
        # Load HR Job datas if field is checked
        if self.hr_job_update:
            # First check if module is installed
            installed = self.env['ir.module.module'].search(
                [('name', '=', 'l10n_ro_hr'),
                 ('state', '=', 'installed')])
            if installed:
                path = data_dir + '/l10n_ro_hr/'
                files = ['hr.job.csv']
                for file1 in files:
                    with tools.file_open(path + file1) as fdata:
                        tools.convert_csv_import(self._cr,
                                                 'l10n_ro_config',
                                                 file1,
                                                 bytes(fdata.read(), 'utf-8'),
                                                 {},
                                                 mode="init",
                                                 noupdate=True)
        # Load SIRUTA datas if field is checked
        if self.caen_update:
            # First check if module is installed
            installed = self.env['ir.module.module'].search(
                [('name', '=', 'l10n_ro_hr_contract'),
                 ('state', '=', 'installed')])
            if installed:
                path = data_dir + '/l10n_ro_hr/'
                files = ['res.company.caen.csv']
                for file1 in files:
                    with tools.file_open(path + file1) as fdata:
                        tools.convert_csv_import(self._cr,
                                                 'l10n_ro_config',
                                                 file1,
                                                 bytes(fdata.read(), 'utf-8'),
                                                 {},
                                                 mode="init",
                                                 noupdate=True)

        # Load Medical Leaves datas if field is checked
        if self.medical_update:
            # First check if module is installed
            installed = self.env['ir.module.module'].search(
                [('name', '=', 'l10n_ro_hr_medical_holidays'),
                 ('state', '=', 'installed')])
            if installed:
                path = data_dir + '/l10n_ro_hr_medical_holidays/'
                files = ['hr.holidays.status.csv',
                         'hr.medical.disease.csv',
                         'hr.medical.emergency.disease.csv',
                         'hr.medical.infecto.disease.csv']
                for file1 in files:
                    with tools.file_open(path + file1) as fdata:
                        tools.convert_csv_import(self._cr,
                                                 'l10n_ro_config',
                                                 file1,
                                                 bytes(fdata.read(), 'utf-8'),
                                                 {},
                                                 mode="init",
                                                 noupdate=True)

        return res
