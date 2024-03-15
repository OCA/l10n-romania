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
    anaf_sync_production_url = fields.Char(string="API production URL")
    anaf_sync_test_url = fields.Char(string="API test URL")
    state = fields.Selection(
        [("test", "Test"), ("production", "Production")],
        default="test",
    )
    anaf_sync_url = fields.Char(compute="_compute_anaf_sync_url")

    @api.depends("state", "anaf_sync_production_url", "anaf_sync_test_url")
    def _compute_anaf_sync_url(self):
        for entry in self:
            if entry.anaf_sync_production_url and entry.anaf_sync_test_url:
                entry.anaf_sync_url = getattr(
                    entry, f"anaf_sync_{entry.state}_url", "anaf_sync_test_url"
                )
            else:
                entry.anaf_sync_url = False

    @api.onchange("scope")
    def _onchange_scope(self):
        if not self.scope:
            self.anaf_sync_production_url = False
            self.anaf_sync_test_url = False
