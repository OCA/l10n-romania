# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.osv import expression


class ResCountryCommune(models.Model):
    _name = "l10n.ro.res.country.commune"
    _description = "Country Cities/Communes"

    @api.model
    def _name_search(
        self, name, args=None, operator="ilike", limit=100, name_get_uid=None
    ):
        args = args or []
        if operator == "ilike" and not (name or "").strip():
            domain = []
        else:
            domain = ["|", ("name", operator, name), ("state_id.code", operator, name)]
        return self._search(
            expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid
        )

    @api.onchange("state_id")
    def _onchange_state_id(self):
        if self.state_id:
            self.zone_id = self.state_id.l10n_ro_zone_id.id
            self.country_id = self.state_id.country_id.id

    @api.onchange("zone_id")
    def _onchange_zone_id(self):
        if self.zone_id:
            self.state_id = False
            self.country_id = self.zone_id.country_id.id

    name = fields.Char("Name", required=True, index=True)
    state_id = fields.Many2one("res.country.state", string="State")
    zone_id = fields.Many2one("l10n.ro.res.country.zone", string="Zone")
    country_id = fields.Many2one("res.country", string="Country")
    siruta = fields.Char("Siruta")
    city_ids = fields.One2many("res.city", "state_id", string="Cities")
