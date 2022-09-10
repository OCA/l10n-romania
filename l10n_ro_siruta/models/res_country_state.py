# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.osv import expression


class ResCountryState(models.Model):
    _name = "res.country.state"
    _inherit = ["res.country.state", "l10n.ro.mixin"]

    @api.model
    def _name_search(
        self, name, args=None, operator="ilike", limit=100, name_get_uid=None
    ):
        if not self.is_l10n_ro_record:
            return super(ResCountryState, self)._name_search(
                name=name,
                args=args,
                operator=operator,
                limit=limit,
                name_get_uid=name_get_uid,
            )
        else:
            args = args or []
            if operator == "ilike" and not (name or "").strip():
                domain = []
            else:
                domain = [
                    "|",
                    ("name", operator, name),
                    ("l10n_ro_zone_id.name", operator, name),
                ]
            return self._search(
                expression.AND([domain, args]),
                limit=limit,
                access_rights_uid=name_get_uid,
            )

    @api.onchange("l10n_ro_zone_id")
    def _onchange_l10n_ro_zone_id(self):
        if self.is_l10n_ro_record:
            if self.l10n_ro_zone_id:
                self.country_id = self.l10n_ro_zone_id.country_id.id

    l10n_ro_zone_id = fields.Many2one("l10n.ro.res.country.zone", string="Zone")
    l10n_ro_commune_ids = fields.One2many(
        "l10n.ro.res.country.commune", "state_id", string="Cities/Communes"
    )
    l10n_ro_city_ids = fields.One2many("res.city", "state_id", string="Cities")
    l10n_ro_siruta = fields.Char("Siruta")
