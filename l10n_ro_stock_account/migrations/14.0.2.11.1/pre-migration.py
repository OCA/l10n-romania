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
                "product.category",
                "product_category",
                "hide_stock_in_out_account",
                "l10n_ro_hide_stock_in_out_account",
            ),
            (
                "product.category",
                "product_category",
                "stock_account_change",
                "l10n_ro_stock_account_change",
            ),
            (
                "product.template",
                "product_template",
                "property_stock_valuation_account_id",
                "l10n_ro_property_stock_valuation_account_id",
            ),
            (
                "stock.location",
                "stock_location",
                "property_account_income_location_id",
                "l10n_ro_property_account_income_location_id",
            ),
            (
                "stock.location",
                "stock_location",
                "property_account_expense_location_id",
                "l10n_ro_property_account_expense_location_id",
            ),
            (
                "stock.location",
                "stock_location",
                "property_stock_valuation_account_id",
                "l10n_ro_property_stock_valuation_account_id",
            ),
            (
                "stock.valuation.layer",
                "stock_valuation_layer",
                "valued_type",
                "l10n_ro_valued_type",
            ),
            (
                "stock.valuation.layer",
                "stock_valuation_layer",
                "invoice_line_id",
                "l10n_ro_invoice_line_id",
            ),
            (
                "stock.valuation.layer",
                "stock_valuation_layer",
                "invoice_id",
                "l10n_ro_invoice_id",
            ),
            (
                "stock.valuation.layer",
                "stock_valuation_layer",
                "account_id",
                "l10n_ro_account_id",
            ),
        ],
    )
