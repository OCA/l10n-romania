# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _l10n_ro_get_anaf_sync(self, scope=None):
        anaf_sync_scope = self.env["l10n.ro.account.anaf.sync.scope"]
        if scope:
            anaf_sync_scope |= anaf_sync_scope.search(
                [("anaf_sync_id.company_id", "=", self.id), ("scope", "=", scope)],
                limit=1,
            )
        return anaf_sync_scope
