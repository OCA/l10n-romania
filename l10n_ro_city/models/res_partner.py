# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo import api, fields, models


class Partner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "l10n.ro.mixin"]

    city_id = fields.Many2one("res.city", domain="[('state_id','=',state_id)]")

    @api.onchange("state_id")
    def onchange_state(self):
        if self.is_l10n_ro_record:
            if self.city_id and self.city_id.state_id != self.state_id:
                self.city_id = None

    @api.onchange("zip")
    def onchange_zip(self):
        if self.zip and self.is_l10n_ro_record:

            domain = [
                ("l10n_ro_prefix_zip", "=", self.zip[:2]),
                ("country_id", "=", self.country_id.id),
            ]
            state = self.env["res.country.state"].search(domain, limit=1)
            if state:
                self.state_id = state

            if self.zip[:2] in ["01", "02", "03", "04", "05", "06"]:
                mapping = {
                    "01": "l10n_ro_city.RO_179141",  # Sector 1
                    "02": "l10n_ro_city.RO_179150",  # Sector 2
                    "03": "l10n_ro_city.RO_179169",  # Sector 3
                    "04": "l10n_ro_city.RO_179178",  # Sector 4
                    "05": "l10n_ro_city.RO_179187",  # Sector 5
                    "06": "l10n_ro_city.RO_179196",  # Sector 6
                }
                city = self.env.ref(mapping[self.zip[:2]])
            else:
                domain = [
                    ("zipcode", "=", self.zip),
                    ("state_id", "=", self.state_id.id),
                ]
                city = self.env["res.city"].search(domain, limit=1)

            if city:
                self.city_id = city
