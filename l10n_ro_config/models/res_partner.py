# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    vat_subjected = fields.Boolean("VAT Legal Statement")

    def _map_vat_country_code(self, country_code):
        country_code_map = {
            "RE": "FR",
            "GP": "FR",
            "MQ": "FR",
            "GF": "FR",
            "EL": "GR",
        }
        return country_code_map.get(country_code, country_code)

    def _split_vat(self, vat):
        # Allowing setting the vat without country code
        vat_country = vat_number = ""
        if vat and vat.isdigit():
            partner = self.search([("vat", "=", vat)], limit=1)
            if partner and partner.country_id:
                vat_country = self._map_vat_country_code(
                    partner.country_id.code.upper()
                ).lower()
                vat_number = vat
        else:
            vat_country, vat_number = super(ResPartner, self)._split_vat(vat)
        return vat_country, vat_number

    @api.onchange("vat_subjected")
    def onchange_vat_subjected(self):
        if not self.env.context.get("skip_ro_vat_change"):
            if self.vat and self.vat.isdigit() and self.vat_subjected:
                vat_country = self._map_vat_country_code(self.country_id.code.upper())
                self.vat = vat_country + self.vat
            elif self.vat and not self.vat.isdigit() and not self.vat_subjected:
                vat_country, vat_number = self._split_vat(self.vat)
                self.vat = vat_number
