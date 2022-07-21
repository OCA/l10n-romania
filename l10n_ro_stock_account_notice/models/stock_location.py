# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    property_notice_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
        company_dependent=True,
        domain="[('company_id', '=', current_company_id)]",
        ondelete="restrict",
        help="Map tax and accounts on picking with notice. ")

