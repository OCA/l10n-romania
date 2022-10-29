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
                "account.account",
                "account_account",
                "nondeductible_account_id",
                "l10n_ro_nondeductible_account_id",
            ),
            (
                "account.tax",
                "account_tax",
                "nondeductible_tax_id",
                "l10n_ro_nondeductible_tax_id",
            ),
            (
                "account.tax",
                "account_tax",
                "nondeductible",
                "l10n_ro_is_nondeductible",
            ),
            (
                "account.tax.repartition.line",
                "account_tax_repartition_line",
                "exclude_from_stock",
                "l10n_ro_exclude_from_stock",
            ),
            (
                "account.tax.repartition.line",
                "account_tax_repartition_line",
                "skip_cash_basis_account_switch",
                "l10n_ro_skip_cash_basis_account_switch",
            ),
            (
                "account.tax.repartition.line",
                "account_tax_repartition_line",
                "nondeductible",
                "l10n_ro_nondeductible",
            ),
            (
                "stock.quant",
                "stock_quant",
                "nondeductible_tax_id",
                "l10n_ro_nondeductible_tax_id",
            ),
            (
                "stock.move",
                "stock_move",
                "nondeductible_tax_id",
                "l10n_ro_nondeductible_tax_id",
            ),
        ],
    )
