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
    if not openupgrade.column_exists(
        env.cr, "res_company", "l10n_ro_property_customs_commission_product_id"
    ) and openupgrade.column_exists(
        env.cr, "res_company", "l10n_ro_property_customs_commision_product_id"
    ):
        openupgrade.rename_fields(
            env,
            [
                (
                    "res.company",
                    "res_company",
                    "l10n_ro_property_customs_commision_product_id",
                    "l10n_ro_property_customs_commission_product_id",
                ),
            ],
        )
