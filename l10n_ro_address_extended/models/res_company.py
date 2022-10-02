# Copyright (C) 2018 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class Company(models.Model):
    _name = "res.company"
    _inherit = ["res.company", "l10n.ro.mixin"]

    l10n_ro_street_staircase = fields.Char(
        string="Romania - Staircase Number",
        compute="_compute_address",
        inverse="_inverse_l10n_ro_street_staircase",
    )

    def _get_company_address_fields(self, partner):
        address_fields = super(Company, self)._get_company_address_fields(partner)
        if self.l10n_ro_accounting:
            address_fields.update(
                {"l10n_ro_street_staircase": partner.l10n_ro_street_staircase}
            )
        return address_fields

    def _inverse_l10n_ro_street_staircase(self):
        for company in self:
            if company.l10n_ro_accounting:
                company.partner_id.l10n_ro_street_staircase = (
                    company.l10n_ro_street_staircase
                )
