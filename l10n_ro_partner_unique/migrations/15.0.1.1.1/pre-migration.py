# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    # Install l10n_ro_config if needed
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        IrModule = env["ir.module.module"]
        IrModule.update_list()

        l10n_ro_config_module = IrModule.search([("name", "=", "l10n_ro_config")])
        if l10n_ro_config_module.state != "installed":
            l10n_ro_config_module.button_immediate_install()
