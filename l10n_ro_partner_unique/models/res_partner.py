# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_vat_nrc_constrain_domain(self):
        self.ensure_one()
        if self.is_l10n_ro_record:
            domain = [
                ("company_id", "=", self.company_id.id if self.company_id else False),
                ("parent_id", "=", False),
                ("vat", "=", self.vat),
                "|",
                ("nrc", "=", self.nrc),
                ("nrc", "=", False),
            ]
        else:
            domain = []
        return domain

    @api.constrains("vat", "nrc")
    def _check_vat_nrc_unique(self):
        for record in self:
            if record.vat and record.is_l10n_ro_record:
                domain = record._get_vat_nrc_constrain_domain()
                found = self.env["res.partner"].search(domain)
                if len(found) > 1:
                    raise ValidationError(
                        _("The VAT and NRC pair (%s, %s) must be unique ids=%s!")
                        % (record.vat, record.nrc, found.ids)
                    )
