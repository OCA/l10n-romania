# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging
import sys

_logger = logging.getLogger(__name__)


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
    if openupgrade.table_exists(env.cr, "res_partner_anaf_status"):
        try:
            openupgrade.rename_tables(
                env.cr,
                [
                    ("res_partner_anaf_status", "l10n_ro_res_partner_anaf_status"),
                    ("res_partner_anaf_scptva", "l10n_ro_res_partner_anaf_scptva"),
                ],
            )
        except Exception as e:
            _logger.info("Error %s." % e)

        try:
            openupgrade.rename_models(
                env.cr,
                [
                    ("res.partner.anaf.status", "l10n.ro.res.partner.anaf.status"),
                    ("res.partner.anaf.scptva", "l10n.ro.res.partner.anaf.scptva"),
                ],
            )
        except Exception as e:
            _logger.info("Error %s." % e)

    fields_to_rename = [
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
    ]

    for field_to_rename in fields_to_rename:
        try:
            openupgrade.rename_fields(env, [field_to_rename])
        except Exception as e:
            _logger.info("Error %s." % e)
            continue
