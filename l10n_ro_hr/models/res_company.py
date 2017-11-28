# Copyright (C) 2017 FOREST AND BIOMASS ROMANIA SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResCompanyCaen(models.Model):
    _name = "res.company.caen"
    _description = "CAEN codes for Romanian Companies"

    code = fields.Char('CAEN code', required=True, help='CAEN code')
    name = fields.Char('CAEN name', required=True, help='CAEN name')
    risk_class = fields.Float('Risk Class', required=True,
                              digits=(0, 2), default=0.0)
    risk_rate = fields.Float('Risk Rate', required=True, digits=(0, 4),
                             default=0.0)

    @api.multi
    def name_get(self):
        return [(caen.id, '%s - %s' % (caen.code and '[%s] ' % caen.code or '',
                                       caen.name))
                for caen in self]


class ResCompany(models.Model):
    _inherit = "res.company"

    caen_id = fields.Many2one(
        'res.company.caen', string='CAEN code', help="Company CAEN code.")
    risk_rate = fields.Float(
        string='Accident Coefficient', related='caen_id.risk_rate',
        digits=(0, 4))
