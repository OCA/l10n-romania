# Copyright (C) 2024 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    send_action = env.ref("l10n_ro_account_edi_ubl.model_account_send_toe_invoice")
    if send_action:
        send_action.code = """
            records.with_context(l10n_ro_edi_manual_action=True).button_process_edi_web_services()
        """  # noqa

    anaf_sync = env["l10n.ro.account.anaf.sync"].search([])
    for sync in anaf_sync:
        env["l10n.ro.account.anaf.sync.scope"].create(
            {
                "anaf_sync_id": sync.id,
                "scope": "e-factura",
                "anaf_sync_production_url": "https://api.anaf.ro/prod/FCTEL/rest",
                "anaf_sync_test_url": "https://api.anaf.ro/test/FCTEL/rest",
                "state": "production" if sync.state == "automatic" else "test",
            }
        )
