# -*- coding: utf-8 -*-
# ©  2015 Forest and Biomass Services Romania
# See README.rst file on addons root folder for license details

from openerp import models, fields, api, tools
import os


class RomaniaConfigSettings(models.TransientModel):
    _name = 'l10n.ro.config.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'l10n.ro.config.settings')
        )
    has_default_company = fields.Boolean(
        string='Has default company',
        readonly=True, change_default=True,
        default=lambda self: bool(
            self.env['res.company'].search_count([]) == 1)
        )
    module_l10n_ro_siruta = fields.Boolean(
        string='Romanian SIRUTA',
        help='This allows you to manage the Romanian Zones, States, Communes, '
             'Cities:\n'
             'The address fields will contain city, commune, state, zone, '
             'country, zip.')
    module_l10n_ro_partner_unique = fields.Boolean(
        'Partners unique by VAT, NRC',
        help='This allows you to have unique partners by VAT and NRC.')
    module_l10n_ro_partner_create_by_vat = fields.Boolean(
        'Romania - Partner Create by VAT',
        help='This allows you to create partners by VAT based on '
             'Ministry of Finance or OpenAPI webservices.')
    siruta_update = fields.Boolean('Load / Update Siruta Data')

    @api.model
    def create(self, values):
        id = super(RomaniaConfigSettings, self).create(values)
        # Hack: to avoid some nasty bug, related fields are not written
        # upon record creation.
        # Hence we write on those fields here.
        vals = {}
        for fname, field in self._columns.iteritems():
            if isinstance(field, fields.Many2one) and fname in values:
                vals[fname] = values[fname]
        self.write(vals)
        return id

    @api.onchange('company_id')
    def onchange_company_id(self):
        # Update related fields
        values = {}
        return {'value': values}

    @api.multi
    def execute(self):
        res = super(RomaniaConfigSettings, self).execute()
        data_dir = os.path.join(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))), 'data')
        # Load SIRUTA datas if field is checked
        wiz = self[0]
        if wiz.siruta_update:
            # First check if module is installed
            installed = self.env['ir.module.module'].search(
                [('name', '=', 'l10n_ro_siruta'),
                 ('state', '=', 'installed')])
            if installed:
                path = data_dir + '/l10n_ro_siruta/'
                files = ['res.country.zone.csv',
                         'res.country.state.csv',
                         'res.country.commune.csv',
                         'res.country.city.csv']
                for file1 in files:
                    with tools.file_open(path + file1) as fp:
                        tools.convert_csv_import(self._cr,
                                                 'l10n_ro_config',
                                                 file1,
                                                 fp.read(),
                                                 {},
                                                 mode="init",
                                                 noupdate=True)
        return res
