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
                "stock.picking",
                "stock_picking",
                "accounting_date",
                "l10n_ro_accounting_date",
            ),
            (
                "stock.valuation.layer",
                "stock_valuation_layer",
                "date_done",
                "l10n_ro_date_done",
            ),
        ],
    )
