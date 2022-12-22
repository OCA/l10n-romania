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
            ("res_country_zone", "l10n_ro_res_country_zone"),
            ("res_country_commune", "l10n_ro_res_country_commune"),
        ],
    )
    openupgrade.rename_fields(
        env,
        [
            ("res.partner", "res_partner", "commune_id", "l10n_ro_commune_id"),
            ("res.partner", "res_partner", "zone_id", "l10n_ro_zone_id"),
            ("res.country.state", "res_country_state", "zone_id", "l10n_ro_zone_id"),
            (
                "res.country.state",
                "res_country_state",
                "commune_ids",
                "l10n_ro_commune_ids",
            ),
            ("res.country.state", "res_country_state", "city_ids", "l10n_ro_city_ids"),
            ("res.country.state", "res_country_state", "siruta", "l10n_ro_siruta"),
            ("res.city", "res_city", "commune_id", "l10n_ro_commune_id"),
            ("res.city", "res_city", "zone_id", "l10n_ro_zone_id"),
        ],
    )
    openupgrade.rename_models(
        env.cr,
        [
            ("res.country.zone", "l10n.ro.res.country.zone"),
            ("res.country.commune", "l10n.ro.res.country.commune"),
        ],
    )
