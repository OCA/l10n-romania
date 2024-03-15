# Copyright (C) 2024 Dakai Soft
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountANAFSyncScope(models.Model):
    _name = "l10n.ro.account.anaf.sync.scope"
    _inherit = ["mail.thread", "l10n.ro.mixin"]
    _description = "Account ANAF Sync Scope"

    anaf_sync_id = fields.Many2one("l10n.ro.account.anaf.sync")
    company_id = fields.Many2one(related="anaf_sync_id.company_id", store=True)
    scope = fields.Selection([])

    state = fields.Selection(
        [("test", "Test"), ("production", "Production")],
        default="test",
    )
    anaf_sync_url = fields.Char(compute="_compute_anaf_sync_url")

    @api.depends("state", "scope")
    def _compute_anaf_sync_url(self):
        for entry in self:
            if not entry.scope:
                entry.anaf_sync_url = False
