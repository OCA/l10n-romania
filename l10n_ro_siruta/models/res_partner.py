# -*- coding: utf-8 -*-
# ©  2015 Forest and Biomass Services Romania
# See README.rst file on addons root folder for license details

from openerp import models, fields, api


class res_partner(models.Model):
    _inherit = "res.partner"

    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id:
            self.commune_id = self.city_id.commune_id.id
            self.state_id = self.city_id.state_id.id
            self.zone_id = self.city_id.zone_id.id
            self.country_id = self.city_id.country_id.id

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
