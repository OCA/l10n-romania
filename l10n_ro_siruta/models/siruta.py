# Copyright (C) 2015 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResCountryZone(models.Model):
    _name = 'res.country.zone'
    _description = 'Country Zones'

    name = fields.Char('Name', required=True, index=True)
    country_id = fields.Many2one('res.country', string="Country")
    state_ids = fields.One2many('res.country.state', 'zone_id', string='State')
    siruta = fields.Char('Siruta')


class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    @api.onchange('zone_id')
    def _onchange_zone_id(self):
        if self.zone_id:
            self.country_id = self.zone_id.country_id.id

    zone_id = fields.Many2one('res.country.zone', string='Zone')
    commune_ids = fields.One2many(
        'res.country.commune', 'state_id', string='Cities/Communes')
    city_ids = fields.One2many('res.city', 'state_id', string='Cities')
    siruta = fields.Char('Siruta')


class ResCountryCommune(models.Model):
    _name = 'res.country.commune'
    _description = 'Country Cities/Communes'

    @api.onchange('state_id')
    def _onchange_state_id(self):
        if self.state_id:
            self.zone_id = self.state_id.zone_id.id
            self.country_id = self.state_id.country_id.id

    @api.onchange('zone_id')
    def _onchange_zone_id(self):
        if self.zone_id:
            self.state_id = False
            self.country_id = self.zone_id.country_id.id

    name = fields.Char('Name', required=True, index=True)
    state_id = fields.Many2one('res.country.state', string='State')
    zone_id = fields.Many2one('res.country.zone', string="Zone")
    country_id = fields.Many2one('res.country', string="Country")
    siruta = fields.Char('Siruta')


class ResCity(models.Model):
    _inherit = 'res.city'

    @api.onchange('commune_id')
    def _onchange_commune_id(self):
        if self.commune_id:
            self.state_id = self.commune_id.state_id.id
            self.zone_id = self.commune_id.zone_id.id
            self.country_id = self.commune_id.country_id.id

    @api.onchange('state_id')
    def _onchange_state_id(self):
        if self.state_id:
            self.commune_id = False
            self.zone_id = self.state_id.zone_id.id
            self.country_id = self.state_id.country_id.id

    @api.onchange('zone_id')
    def _onchange_zone_id(self):
        if self.zone_id:
            self.commune_id = False
            self.state_id = False
            self.country_id = self.zone_id.country_id.id

    commune_id = fields.Many2one('res.country.commune', string='City/Commune')
    zone_id = fields.Many2one('res.country.zone', string="Zone")
    siruta = fields.Char('Siruta')
