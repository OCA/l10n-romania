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
            ("res_partner_anaf_status", "l10n_ro_res_partner_anaf_status"),
            ("res_partner_anaf_scptva", "l10n_ro_res_partner_anaf_scptva"),
        ],
    )
    openupgrade.rename_fields(
        env,
        [
            ("res.partner", "res_partner", "old_name", "l10n_ro_old_name"),
            (
                "res.partner",
                "res_partner",
                "active_anaf_line_ids",
                "l10n_ro_active_anaf_line_ids",
            ),
            (
                "res.partner",
                "res_partner",
                "l10n_ro_vat_subjected_anaf_line_ids",
                "l10n_ro_l10n_ro_vat_subjected_anaf_line_ids",
            ),
        ],
    )
    openupgrade.rename_models(
        env.cr,
        [
            ("res.partner.anaf.status", "l10n.ro.res.partner.anaf.status"),
            ("res.partner.anaf.scptva", "l10n.ro.res.partner.anaf.scptva"),
        ],
    )
