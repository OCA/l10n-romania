# -*- coding: utf-8 -*-
# ©  2015 Forest and Biomass Services Romania
# See README.rst file on addons root folder for license details

from openerp import models, fields, api


class ResCountryZone(models.Model):
    _name = 'res.country.zone'
    _description = 'Country Zones'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('name', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search(
                [('country_id.name', operator, name)] + args, limit=limit)
        return recs.name_get()

    name = fields.Char('Name', required=True, index=True)
    country_id = fields.Many2one('res.country', string="Country")
    state_ids = fields.One2many('res.country.state', 'zone_id', string='State')
    siruta = fields.Char('Siruta')


class ResCountryState(models.Model):
    _name = 'res.country.state'
    _inherit = 'res.country.state'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('name', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search(
                [('zone_id.name', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search(
                [('country_id.name', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.onchange('zone_id')
    def _onchange_zone_id(self):
        if self.zone_id:
            self.country_id = self.zone_id.country_id.id

    zone_id = fields.Many2one('res.country.zone', string='Zone')
    commune_ids = fields.One2many(
        'res.country.commune', 'state_id', string='Cities/Communes')
    city_ids = fields.One2many('res.country.city', 'state_id', string='Cities')
    siruta = fields.Char('Siruta')


class ResCountryCommune(models.Model):
    _name = 'res.country.commune'
    _description = 'Country Cities/Communes'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('name', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search(
                [('state_id.name', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search(
                [('zone_id.name', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search(
                [('country_id.name', operator, name)] + args, limit=limit)
        return recs.name_get()

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


class ResCountryCity(models.Model):
    _name = 'res.country.city'
    _description = 'Country Cities'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('name', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search(
                [('commune_id.name', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search(
                [('state_id.name', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search(
                [('zone_id.name', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search(
                [('country_id.name', operator, name)] + args, limit=limit)
        return recs.name_get()

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

    name = fields.Char('Name', required=True, index=True)
    commune_id = fields.Many2one('res.country.commune', string='City/Commune')
    state_id = fields.Many2one('res.country.state', string='State')
    zone_id = fields.Many2one('res.country.zone', string="Zone")
    country_id = fields.Many2one('res.country', string="Country")
    siruta = fields.Char('Siruta')
