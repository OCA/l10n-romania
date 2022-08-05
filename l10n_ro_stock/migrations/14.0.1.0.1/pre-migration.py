# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import sys


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

    # ??
    views = [
        "l10n_ro_config.res_config_settings_view_form",
        "l10n_ro_config.res_config_settings_account_view_form",
    ]
    openupgrade.delete_records_safely_by_xml_id(env, views)
