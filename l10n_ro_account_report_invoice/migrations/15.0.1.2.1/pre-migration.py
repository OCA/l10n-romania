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
                "res.company",
                "res_company",
                "invoice_no_signature_text",
                "l10n_ro_no_signature_text",
            ),
            (
                "res.config.settings",
                "res_config_settings",
                "invoice_no_signature_text",
                "l10n_ro_no_signature_text",
            ),
            ("account.move", "account_move", "currency_rate", "l10n_ro_currency_rate"),
            (
                "account.payment",
                "account_payment",
                "currency_rate",
                "l10n_ro_currency_rate",
            ),
        ],
    )

    views = [
        "l10n_ro_account_report_invoice.res_config_settings_view_form",
        "l10n_ro_account_report_invoice.l10n_ro_view_move_form",
        "l10n_ro_account_report_invoice.l10n_ro_report_invoice_document",
    ]
    openupgrade.delete_records_safely_by_xml_id(env, views)
