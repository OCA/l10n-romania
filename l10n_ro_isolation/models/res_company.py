# Copyright (C) 2015 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _check_is_l10n_ro_record(self, company=False):
        if not company:
            company = self
        else:
            company = self.browse(company)
        return company.l10n_ro_accounting
