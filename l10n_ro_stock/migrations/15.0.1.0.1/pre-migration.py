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
    openupgrade.rename_fields(
        env,
        [
            (
                "stock.location",
                "stock_location",
                "merchandise_type",
                "l10n_ro_merchandise_type",
            ),
            (
                "stock.warehouse",
                "stock.warehouse",
                "wh_consume_loc_id",
                "l10n_ro_wh_consume_loc_id",
            ),
            (
                "stock.warehouse",
                "stock.warehouse",
                "wh_usage_loc_id",
                "l10n_ro_wh_usage_loc_id",
            ),
            (
                "stock.warehouse",
                "stock.warehouse",
                "consume_type_id",
                "l10n_ro_consume_type_id",
            ),
            (
                "stock.warehouse",
                "stock.warehouse",
                "usage_type_id",
                "l10n_ro_usage_type_id",
            ),
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
