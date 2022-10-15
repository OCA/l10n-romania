# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import sys

from odoo import SUPERUSER_ID, api


def install(package):
    try:
        __import__(package)
    except Exception:
        import subprocess

        subprocess.call([sys.executable, "-m", "pip", "install", package])


install("openupgradelib")

try:
    from openupgradelib import openupgrade
except ImportError:
    openupgrade = None


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    openupgrade.rename_tables(
        env.cr,
        [
            ("stock_storage_sheet", "l10n_ro_stock_storage_sheet"),
            ("stock_storage_sheet_line", "l10n_ro_stock_storage_sheet_line"),
        ],
    )
    openupgrade.rename_models(
        env.cr,
        [
            ("stock.storage.sheet", "l10n.ro.stock.storage.sheet"),
            ("stock.storage.sheet.line", "l10n.ro.stock.storage.sheet.line"),
        ],
    )
    # Install l10n_ro_config if needed
    with api.Environment.manage():
        env = api.Environment(env.cr, SUPERUSER_ID, {})
        IrModule = env["ir.module.module"]
        IrModule.update_list()

        l10n_ro_config_module = IrModule.search([("name", "=", "l10n_ro_config")])
        if l10n_ro_config_module.state != "installed":
            l10n_ro_config_module.button_immediate_install()
