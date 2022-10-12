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
                "stock.landed.cost",
                "stock_landed_cost",
                "tax_value",
                "l10n_ro_tax_value",
            ),
            (
                "stock.landed.cost",
                "stock_landed_cost",
                "tax_id",
                "l10n_ro_tax_id",
            ),
        ],
    )
