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
                "stock.move.line",
                "stock_move_line",
                "sale_line_id",
                "l10n_ro_sale_line_id",
            ),
            (
                "stock.move.line",
                "stock_move_line",
                "purchase_line_id",
                "l10n_ro_purchase_line_id",
            ),
            (
                "stock.move.line",
                "stock_move_line",
                "currency_id",
                "l10n_ro_currency_id",
            ),
            ("stock.move.line", "stock_move_line", "price_unit", "l10n_ro_price_unit"),
            (
                "stock.move.line",
                "stock_move_line",
                "price_subtotal",
                "l10n_ro_price_subtotal",
            ),
            ("stock.move.line", "stock_move_line", "price_tax", "l10n_ro_price_tax"),
            (
                "stock.move.line",
                "stock_move_line",
                "price_total",
                "l10n_ro_price_total",
            ),
            ("stock.picking", "stock_picking", "currency_id", "l10n_ro_currency_id"),
            (
                "stock.picking",
                "stock_picking",
                "amount_untaxed",
                "l10n_ro_amount_untaxed",
            ),
            ("stock.picking", "stock_picking", "amount_tax", "l10n_ro_amount_tax"),
            ("stock.picking", "stock_picking", "amount_total", "l10n_ro_amount_total"),
            ("stock.picking", "stock_picking", "is_internal", "l10n_ro_is_internal"),
        ],
    )
