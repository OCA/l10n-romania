# -*- coding: utf-8 -*-
# ©  2015 Forest and Biomass Services Romania
# See README.rst file on addons root folder for license details

from openerp import models, fields


class RomaniaConfigSettings(models.TransientModel):
    _name = 'l10n.ro.config.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one('res.company', string='Company',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'l10n.ro.config.settings')
        )
    has_default_company = fields.Boolean(string='Has default company',
        readonly=True, change_default=True,
        default=lambda self: bool(
            self.env['res.company'].search_count([]) == 1)
        )
    module_l10n_ro_siruta = fields.Boolean(string='Romanian SIRUTA',
        help='This allows you to manage the Romanian Zones, States, Communes, '
             'Cities:\n'
             'The address fields will contain city, commune, state, zone, '
             'country, zip.')
    module_partner_create_by_vat = fields.Boolean('Create Partners by VAT',
        help='This allows you to create partners based on VAT:\n'
             'Romanian partners will be create based on Ministry of Finance / '
             'openapi.ro Webservices Datas\n'
             'European partners will be create based on VIES Website Datas '
             '(for countries that allow). \n')

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

    @api.multi
    def execute(self):
        res = super(RomaniaConfigSettings, self).execute()
        return res
