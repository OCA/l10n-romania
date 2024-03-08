# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ro_account_anaf_sync_id = fields.Many2one(
        "l10n.ro.account.anaf.sync",
        string="Romania - Account ANAF Sync",
        compute="_compute_l10n_ro_account_anaf_sync_id",
    )

    def _compute_l10n_ro_account_anaf_sync_id(self):
        for company in self:
            domain = [("company_id", "=", company.id)]
            company.l10n_ro_account_anaf_sync_id = self.env[
                "l10n.ro.account.anaf.sync"
            ].search(domain, limit=1)
