# Copyright (C) 2025 NextERP Romania
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

    openupgrade.logged_query(
        env.cr,
        """
        UPDATE res_partner
        SET l10n_ro_edi_ubl_no_send_cnp = True
        FROM res_country
        WHERE res_partner.country_id = res_country.id
            AND res_country.code = 'RO'
            AND res_partner.is_company = False
            AND res_partner.parent_id IS NULL;
        """,
    )
