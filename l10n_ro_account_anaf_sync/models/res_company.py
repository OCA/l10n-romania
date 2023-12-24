# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ro_account_anaf_sync_ids = fields.One2many(
        "l10n.ro.account.anaf.sync",
        "company_id",
        string="Romania - Account ANAF Sync",
    )

    def get_l10n_ro_anaf_sync(self, scope="both"):
        self.ensure_one()
        value_list = ["both"]
        if scope == "e-invoice":
            value_list += ["e-invoice"]
        elif scope == "e-transport":
            value_list += ["e-transport"]
        anaf_sync = self.l10n_ro_account_anaf_sync_ids.filtered(
            lambda r: r.scope in value_list
        )
        if anaf_sync:
            return anaf_sync[0]
        return UserError(
            _("Error, no ANAF Sync found for %s, please create one!") % scope
        )
