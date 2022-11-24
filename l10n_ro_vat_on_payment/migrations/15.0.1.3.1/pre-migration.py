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
            ("res_partner_anaf", "l10n_ro_res_partner_anaf"),
        ],
    )
    openupgrade.rename_fields(
        env,
        [
            (
                "res.partner",
                "res_partner",
                "vat_on_payment",
                "l10n_ro_vat_on_payment",
            ),
            (
                "res.partner",
                "res_partner",
                "anaf_history",
                "l10n_ro_anaf_history",
            ),
        ],
    )
    openupgrade.rename_models(
        env.cr,
        [
            ("res.partner.anaf", "l10n.ro.res.partner.anaf"),
        ],
    )
    views = [
        "l10n_ro_vat_on_payment.partners_form_add_vat_payment",
        "l10n_ro_vat_on_payment.view_partner_anaf_form",
    ]
    openupgrade.delete_records_safely_by_xml_id(env, views)

    # Install l10n_ro_config if needed
    env = api.Environment(env.cr, SUPERUSER_ID, {})
    IrModule = env["ir.module.module"]
    IrModule.update_list()

    l10n_ro_config_module = IrModule.search([("name", "=", "l10n_ro_config")])
    if l10n_ro_config_module.state != "installed":
        l10n_ro_config_module.button_immediate_install()
