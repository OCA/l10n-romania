# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    IrModule = env["ir.module.module"]
    IrModule.update_list()

    l10n_ro_stock_account_determination_module = IrModule.search(
        [("name", "=", "l10n_ro_stock_account_determination")]
    )
    if l10n_ro_stock_account_determination_module.state not in (
        "installed",
        "to install",
        "to upgrade",
    ):
        l10n_ro_stock_account_determination_module.button_install()
