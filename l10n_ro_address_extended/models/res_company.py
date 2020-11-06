# Copyright (C) 2018 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    street_staircase = fields.Char(
        "Staircase Number",
        compute="_compute_address",
        inverse="_inverse_street_staircase",
    )

    def _get_company_address_fields(self, partner):
        address_fields = super(Company, self)._get_company_address_fields(partner)
        address_fields.update({"street_staircase": partner.street_staircase})
        return address_fields

    def _inverse_street_staircase(self):
        for company in self:
            company.partner_id.street_staircase = company.street_staircase
