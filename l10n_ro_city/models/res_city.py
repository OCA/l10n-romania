# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class CountryCity(models.Model):
    _name = "res.city"
    _inherit = ["res.city", "l10n.ro.mixin"]

    l10n_ro_siruta = fields.Char(string="Romania - Siruta")
    l10n_ro_municipality = fields.Char(string="Romania - Municipality")
    zipcode = fields.Char(index=True)

    @api.depends("country_id")
    def _compute_is_l10n_ro_record(self):
        for city in self:
            city.is_l10n_ro_record = not city.country_id or city.country_id.code == "RO"

    def _compute_display_name(self):
        rest = self
        for record in self:
            if record.country_id and record.country_id.code != "RO":
                continue
            if (
                record.l10n_ro_municipality
                and record.name not in record.l10n_ro_municipality
            ):
                record.display_name = (
                    f"{record.name} "
                    f"({record.l10n_ro_municipality}) "
                    f"({record.state_id.code})"
                )
            else:
                record.display_name = f"{record.name} ({record.state_id.code})"
            rest -= record
        return super(CountryCity, rest)._compute_display_name()
