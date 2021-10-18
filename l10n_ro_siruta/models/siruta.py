# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.osv import expression


class ResCountryZone(models.Model):
    _name = "res.country.zone"
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
    state_ids = fields.One2many("res.country.state", "zone_id", string="State")
    siruta = fields.Char("Siruta")


class ResCountryState(models.Model):
    _inherit = "res.country.state"

    @api.model
    def _name_search(
        self, name, args=None, operator="ilike", limit=100, name_get_uid=None
    ):
        args = args or []
        if operator == "ilike" and not (name or "").strip():
            domain = []
        else:
            domain = ["|", ("name", operator, name), ("zone_id.name", operator, name)]
        return self._search(
            expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid
        )

    @api.onchange("zone_id")
    def _onchange_zone_id(self):
        if self.zone_id:
            self.country_id = self.zone_id.country_id.id

    zone_id = fields.Many2one("res.country.zone", string="Zone")
    commune_ids = fields.One2many(
        "res.country.commune", "state_id", string="Cities/Communes"
    )
    city_ids = fields.One2many("res.city", "state_id", string="Cities")
    siruta = fields.Char("Siruta")


class ResCountryCommune(models.Model):
    _name = "res.country.commune"
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
            self.zone_id = self.state_id.zone_id.id
            self.country_id = self.state_id.country_id.id

    @api.onchange("zone_id")
    def _onchange_zone_id(self):
        if self.zone_id:
            self.state_id = False
            self.country_id = self.zone_id.country_id.id

    name = fields.Char("Name", required=True, index=True)
    state_id = fields.Many2one("res.country.state", string="State")
    zone_id = fields.Many2one("res.country.zone", string="Zone")
    country_id = fields.Many2one("res.country", string="Country")
    siruta = fields.Char("Siruta")
    city_ids = fields.One2many("res.city", "state_id", string="Cities")


class ResCity(models.Model):
    _inherit = "res.city"

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
                ("commune_id.name", operator, name),
            ]
        return self._search(
            expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid
        )

    @api.onchange("commune_id")
    def _onchange_commune_id(self):
        if self.commune_id:
            self.state_id = self.commune_id.state_id.id
            self.zone_id = self.commune_id.zone_id.id
            self.country_id = self.commune_id.country_id.id

    @api.onchange("state_id")
    def _onchange_state_id(self):
        if self.state_id:
            self.commune_id = False
            self.zone_id = self.state_id.zone_id.id
            self.country_id = self.state_id.country_id.id

    @api.onchange("zone_id")
    def _onchange_zone_id(self):
        if self.zone_id:
            self.commune_id = False
            self.state_id = False
            self.country_id = self.zone_id.country_id.id

    commune_id = fields.Many2one("res.country.commune", string="City/Commune")
    zone_id = fields.Many2one("res.country.zone", string="Zone")
    municipality = fields.Char(related="commune_id.name")
