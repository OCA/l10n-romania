# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return

    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        IrModule = env["ir.module.module"]
        IrModule.update_list()

        ro_comps = env["res.company"].search([("romanian_accounting", "=", True)])
        if ro_comps:
            stock_account_notice_module = IrModule.search(
                [("name", "=", "l10n_ro_stock_account_notice")]
            )
            stock_account_notice_module.button_install()
