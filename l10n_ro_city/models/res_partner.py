# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Partner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "l10n.ro.mixin"]

    city_id = fields.Many2one("res.city", domain="[('state_id','=',state_id)]")

    @api.onchange("state_id")
    def onchange_state(self):
        if self.country_id.code == "RO":
            if self.city_id and self.city_id.state_id != self.state_id:
                self.city_id = None

    @api.onchange("zip")
    def onchange_zip(self):
        if self.zip and self.country_id.code == "RO":
            state_b = self.env.ref("base.RO_B")

            domain = [
                ("l10n_ro_prefix_zip", "=", self.zip[:2]),
                ("country_id", "=", self.country_id.id),
            ]
            state = self.env["res.country.state"].search(domain, limit=1)
            if state:
                if self.state_id and self.state_id != state:
                    raise UserError(
                        _(f"The state {state.name} doesn't match the zip code")
                    )
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
                if self.state_id != state_b:
                    raise UserError(
                        _(
                            f"The city {city.name} doesn't match the"
                            f" zip code and the state {state.name}"
                        )
                    )
            else:
                domain = [
                    ("zipcode", "=", self.zip),
                    ("state_id", "=", self.state_id.id),
                ]
                city = self.env["res.city"].search(domain, limit=1)

            if city:
                self.write(
                    {
                        "city_id": city.id,
                        "city": city.name,
                        "state_id": city.state_id.id,
                    }
                )

    @api.onchange("city_id")
    def _onchange_city_id(self):
        backup_zip = self.zip
        backup_city = self.city
        res = super()._onchange_city_id()
        if not self.zip and backup_zip:
            self.zip = backup_zip
        if not self.city and backup_city:
            self.city = backup_city
        return res
