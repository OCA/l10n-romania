# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_vat_nrc_constrain_domain(self):
        self.ensure_one()
        vat = (self.vat or "").strip().upper()
        nrc = (self.nrc or "").strip().upper() if self.nrc else ""

        vat_2 = vat.replace("RO", "")
        vat_1 = "RO" + vat_2

        domain = [
            ("company_id", "=", self.company_id.id if self.company_id else False),
            ("parent_id", "=", False),
            ("id", "!=", self.id),
            ("is_company", "=", True),
            "&",
            "|",
            ("vat", "=ilike", vat_1),
            ("vat", "=ilike", vat_2),
            "|",
            ("nrc", "=ilike", nrc),
            ("nrc", "=", False),
        ]
        return domain

    @api.constrains("vat", "nrc", "is_company")
    def _check_vat_nrc_unique(self):
        for record in self.filtered("is_company"):
            if record.parent_id:
                continue
            if record.vat and record.is_l10n_ro_record:
                domain = record._get_vat_nrc_constrain_domain()
                if self.env["res.partner"].search(domain, limit=1):
                    raise ValidationError(
                        self.env._(
                            "The VAT and NRC pair (%(vat)s, %(nrc)s) must be unique!",
                            vat=record.vat,
                            nrc=record.nrc,
                        )
                    )
