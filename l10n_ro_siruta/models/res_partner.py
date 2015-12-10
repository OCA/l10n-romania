# -*- coding: utf-8 -*-
# ©  2015 Forest and Biomass Services Romania
# See README.rst file on addons root folder for license details

from openerp import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id:
            self.commune_id = self.city_id.commune_id.id
            self.state_id = self.city_id.state_id.id
            self.zone_id = self.city_id.zone_id.id
            self.country_id = self.city_id.country_id.id

    @api.model
    def _address_fields(self):
        """ Extends list of address fields with city_id, commune_id, zone_id
        to be synced from the parent when the `use_parent_address`
        flag is set. """
        new_list = ['city_id', 'commune_id', 'zone_id']
        return super(ResPartner, self)._address_fields() + new_list

    @api.one
    def _search_city(self):
        city_obj = self.env['res.country.city']
        if self.state_id:
            city_id = city_obj.search([("name", "ilike", self.city),
                                       ("state_id", "=", self.state_id.id)])
            if city_id:
                self.city_id = city_id[0].id
        else:
            city_id = city_obj.search([("name", "ilike", self.city)])
            if city_id:
                self.city_id = city_id[0].id

    @api.model
    def _install_l10n_ro_siruta(self):
        """Updates city_id field by searching on city and state_id."""
        partners = self.search([("city", "!=", False)])
        partners._search_city()

    city_id = fields.Many2one('res.country.city',
                              string='City',
                              ondelete='set null',
                              index=True)
    city = fields.Char(related='city_id.name',
                       string='City',
                       store=True)
    commune_id = fields.Many2one('res.country.commune',
                                 string='City/Commune',
                                 ondelete='set null',
                                 index=True)
    zone_id = fields.Many2one('res.country.zone',
                              string='Zone',
                              ondelete='set null',
                              index=True)
