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
    openupgrade.rename_tables(
        env.cr,
        [
            ("account_period_closing", "l10n_ro_account_period_closing"),
            ("account_period_closing_wizard", "l10n_ro_account_period_closing_wizard"),
        ],
    )
    openupgrade.rename_fields(
        env,
        [
            (
                "account.account",
                "account_account",
                "close_check",
                "l10n_ro_close_check",
            ),
            ("account.move", "account_move", "close_id", "l10n_ro_close_id"),
        ],
    )
    openupgrade.rename_models(
        env.cr,
        [
            ("account.period.closing", "l10n.ro.account.period.closing"),
            ("account.period.closing.wizard", "l10n.ro.account.period.closing.wizard"),
        ],
    )
