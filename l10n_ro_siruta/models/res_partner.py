# Copyright (C) 2015 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "l10n.ro.mixin"]

    @api.onchange("city_id")
    def _onchange_city_id(self):
        super(ResPartner, self)._onchange_city_id()
        if self.is_l10n_ro_record:
            if self.city_id:
                self.l10n_ro_commune_id = self.city_id.l10n_ro_commune_id.id
                self.l10n_ro_zone_id = self.city_id.l10n_ro_zone_id.id
                self.country_id = self.city_id.country_id.id

    @api.model
    def _address_fields(self):
        """Extends list of address fields with city_id, l10n_ro_commune_id, l10n_ro_zone_id
        to be synced from the parent when the `use_parent_address`
        flag is set."""
        new_list = ["city_id", "l10n_ro_commune_id", "l10n_ro_zone_id"]
        return super(ResPartner, self)._address_fields() + new_list

    @api.model
    def _install_l10n_ro_siruta(self):
        """Update commune and zone fields for partners."""
        # Find records with city_id completed but not the commune
        records = self.search(
            [("city_id", "!=", False), ("l10n_ro_commune_id", "=", False)]
        )

        # Launch onchange city_id for each partner
        for partner in records:
            partner._onchange_city_id()
        _logger.info("%d partners updated installing module.", len(records))

    l10n_ro_commune_id = fields.Many2one(
        "l10n.ro.res.country.commune",
        string="City/Commune",
        ondelete="set null",
        index=True,
    )
    l10n_ro_zone_id = fields.Many2one(
        "l10n.ro.res.country.zone", string="Zone", ondelete="set null", index=True
    )
