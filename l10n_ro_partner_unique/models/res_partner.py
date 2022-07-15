# Copyright (C) 2015 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_vat_nrc_constrain_domain(self):
        domain = [
            ("company_id", "=", self.company_id.id if self.company_id else False),
            ("parent_id", "=", False),
            ("vat", "=", self.vat),
            "|",
            ("nrc", "=", self.nrc),
            ("nrc", "=", False),
        ]
        return domain

    @api.constrains('vat', 'nrc')
    def _check_vat_nrc_unique(self):
        for record in self:
            if record.vat:
                domain = record._get_vat_nrc_constrain_domain()
                results = self.env['res.partner'].search(domain)
                if len(results) > 1:
                    raise ValidationError(
                        _("The VAT and NRC pair (%s, %s) must be unique ids=%s!") %
                        (record.vat, record.nrc, record.ids))
