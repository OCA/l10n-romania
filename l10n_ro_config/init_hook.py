# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

logger = logging.getLogger(__name__)


def pre_init_hook(cr):
    """
    The objective of this hook is to speed up the installation
    of the module on an existing Odoo instance.

    Without this script, if a database has a few hundred thousand
    partners, which is not unlikely, the update will take
    at least a few hours.

    The pre init script writes the digits from vat fields to the
    l10n_ro_vat_number so that it is not computed by the install.

    """
    store_field_l10n_ro_vat_number(cr)


def store_field_l10n_ro_vat_number(cr):
    cr.execute(
        """SELECT column_name
           FROM information_schema.columns
           WHERE table_name='res_partner' AND column_name='l10n_ro_vat_number'"""
    )
    if not cr.fetchone():
        cr.execute(
            """
            ALTER TABLE res_partner ADD COLUMN l10n_ro_vat_number varchar;
            COMMENT ON COLUMN res_partner.l10n_ro_vat_number IS 'VAT number digits';
            """
        )

        logger.info("Computing field l10n_ro_vat_number on res.partner")

        cr.execute(
            r"""
            UPDATE res_partner partner
            SET l10n_ro_vat_number = NULLIF(regexp_replace(vat, '[^\.\d]', '', 'g'), '')
            """
        )
