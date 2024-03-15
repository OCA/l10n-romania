# Copyright (C) 2024 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return

    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})

        anaf_sync = env["l10n.ro.account.anaf.sync"].search([])
        for sync in anaf_sync:
            env["l10n.ro.account.anaf.sync.scope"].create(
                {
                    "anaf_sync_id": sync.id,
                    "scope": "e-factura",
                    "state": "production" if sync.state == "automatic" else "test",
                }
            )
