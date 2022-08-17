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
            ("res.partner", "res_partner", "mean_transp", "l10n_ro_mean_transp"),
            ("res.users", "res_users", "mean_transp", "l10n_ro_mean_transp"),
            ("stock.picking", "stock_picking", "delegate_id", "l10n_ro_delegate_id"),
            ("stock.picking", "stock_picking", "mean_transp", "l10n_ro_mean_transp"),
        ],
    )
