# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


import re

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
        zip_raw = (self.zip or "").strip()
        country_code = self.country_id.code if self.country_id else None
        if not zip_raw or country_code != "RO":
            return

        # Normalizează: păstrează doar cifre, apoi left-pad la 6 cifre (standard RO)
        zip_digits = re.sub(r"\D", "", zip_raw)
        if not zip_digits:
            return
        if len(zip_digits) <= 6:
            zip_normalized = zip_digits.zfill(6)
        else:
            zip_normalized = zip_digits[:6]

        self.zip = zip_normalized
        zip_prefix = zip_normalized[:2]
        domain = [
            ("l10n_ro_prefix_zip", "=", zip_prefix),
            ("country_id", "=", self.country_id.id),
        ]
        state = self.env["res.country.state"].search(domain, limit=1)

        if state:
            if self.state_id and self.state_id != state:
                raise UserError(
                    _("The state %s doesn't match the zip code") % state.name
                )
            self.state_id = state

        bucharest_prefixes = {"01", "02", "03", "04", "05", "06"}
        if zip_prefix in bucharest_prefixes:
            mapping = {
                "01": "l10n_ro_city.RO_179141",  # Sector 1
                "02": "l10n_ro_city.RO_179150",  # Sector 2
                "03": "l10n_ro_city.RO_179169",  # Sector 3
                "04": "l10n_ro_city.RO_179178",  # Sector 4
                "05": "l10n_ro_city.RO_179187",  # Sector 5
                "06": "l10n_ro_city.RO_179196",  # Sector 6
            }
            city = self.env.ref(mapping[zip_prefix], raise_if_not_found=False)

            state_b = self.env.ref("base.RO_B", raise_if_not_found=False)
            if (
                city
                and self.state_id
                and state_b
                and self.state_id != state_b
                and "skip_ro_vat_change" not in self.env.context
            ):
                raise UserError(
                    _(
                        f"The city {city.name} doesn't match the"
                        f" zip code and the state {state.name}"
                    )
                )
        else:
            # Caută reședința după cod poștal și stat (dacă statul e cunoscut)
            domain = [("zipcode", "=", zip_normalized)]
            if self.state_id:
                domain.append(("state_id", "=", self.state_id.id))
            city = self.env["res.city"].search(domain, limit=1)

        if city:
            self.city = city.name
            self.city_id = city
            self.state_id = city.state_id

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

    def get_zip_from_city(self):
        zipcode = self.zip or self.city_id.zipcode
        return zipcode
