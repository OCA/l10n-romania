# -*- coding: utf-8 -*-
# ©  2015-2020 Deltatech
# See README.rst file on addons root folder for license details

from lxml import etree

from odoo import api, models, fields
from odoo.tools.translate import _


class Partner(models.Model):
    _inherit = 'res.partner'

    city_id = fields.Many2one('res.city', domain="[('state_id','=',state_id)]")

    @api.onchange('state_id')
    def onchange_state(self):
        res = {'domain': {'city_id': [('state_id', '=', self.state_id.id)]}}
        return res
