# Copyright (C) 2015 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    commune_id = fields.Many2one(
        "res.country.commune", string="City/Commune", ondelete="set null", index=True
    )
    zone_id = fields.Many2one(
        "res.country.zone", string="Zone", ondelete="set null", index=True
    )

    @api.onchange("city_id")
    def _onchange_city_id(self):
        super(ResPartner, self)._onchange_city_id()
        if self.city_id:
            self.commune_id = self.city_id.commune_id.id
            self.zone_id = self.city_id.zone_id.id

    @api.model
    def _address_fields(self):
        """ Extends list of address fields with city_id, commune_id, zone_id
        to be synced from the parent when the `use_parent_address`
        flag is set. """
        new_list = ["city_id", "commune_id", "zone_id"]
        return super(ResPartner, self)._address_fields() + new_list

    @api.onchange("commune_id")
    def _onchange_commune_id(self):
        if self.city_id.commune_id != self.commune_id:
            self.city_id = False

        if self.commune_id:
            domain = [("commune_id", "=", self.commune_id.id)]
            return {"domain": {"city_id": domain}}

    @api.onchange("state_id")
    def _onchange_state_id(self):
        if self.commune_id.state_id != self.state_id:
            self.commune_id = False
        if self.state_id:
            domain = [("state_id", "=", self.state_id.id)]
            return {"domain": {"commune_id": domain}}

    def write(self, vals):
        if "city_id" in vals and "city" not in vals:
            city = self.env["res.city"].browse(vals["city_id"])
            vals["city"] = city.name
        return super(ResPartner, self).write(vals)
