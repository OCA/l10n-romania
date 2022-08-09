# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.osv import expression


class ResCountryZone(models.Model):
    _name = "l10n.ro.res.country.zone"
    _description = "Country Zones"

    @api.model
    def _name_search(
        self, name, args=None, operator="ilike", limit=100, name_get_uid=None
    ):
        args = args or []
        if operator == "ilike" and not (name or "").strip():
            domain = []
        else:
            domain = [
                "|",
                ("name", operator, name),
                ("country_id.code", operator, name),
            ]
        return self._search(
            expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid
        )

    name = fields.Char("Name", required=True, index=True)
    country_id = fields.Many2one("res.country", string="Country")
    state_ids = fields.One2many("res.country.state", "l10n_ro_zone_id", string="State")
    siruta = fields.Char("Siruta")
