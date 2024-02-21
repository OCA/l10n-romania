# Copyright (C) 2023 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return

    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})

        send_action = env.ref("l10n_ro_account_edi_ubl.model_account_send_toe_invoice")
        if send_action:
            send_action.code = """
                records.with_context(l10n_ro_edi_manual_action=True).action_process_edi_web_services()
            """  # noqa
