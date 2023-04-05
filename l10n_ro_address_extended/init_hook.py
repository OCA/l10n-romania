# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

logger = logging.getLogger(__name__)


def pre_init_hook(cr):
    store_field_l10n_ro_street_staircase(cr)


def store_field_l10n_ro_street_staircase(cr):
    cr.execute(
        """SELECT column_name
           FROM information_schema.columns
           WHERE table_name='res_partner' AND column_name='l10n_ro_street_staircase'"""
    )
    if not cr.fetchone():
        cr.execute(
            """
            ALTER TABLE res_partner ADD COLUMN l10n_ro_street_staircase varchar;
            """
        )

        logger.info("Computing field l10n_ro_street_staircase on res.partner")

        cr.execute(
            r"""
            UPDATE res_partner partner
            SET l10n_ro_street_staircase =
                split_part(split_part(upper(street), 'SC.', 2), ',',1)
            WHERE country_id=(SELECT id FROM res_country WHERE code='RO')
            """
        )
