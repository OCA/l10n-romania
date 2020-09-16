# ©  2008-2020 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import fields, models


class ResCountry(models.Model):
    _inherit = "res.country"

    intrastat = fields.Boolean(string="Intrastat member")
