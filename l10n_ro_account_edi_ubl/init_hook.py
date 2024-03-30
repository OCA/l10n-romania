# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

logger = logging.getLogger(__name__)


def pre_init_hook(env):
    add_field_l10n_ro_is_government_institution(env)


def add_field_l10n_ro_is_government_institution(env):
    env.cr.execute(
        """SELECT column_name
           FROM information_schema.columns
           WHERE table_name='res_partner' AND column_name='l10n_ro_is_government_institution'"""
    )
    if not env.cr.fetchone():
        env.cr.execute(
            """
            ALTER TABLE res_partner ADD COLUMN l10n_ro_is_government_institution
            boolean DEFAULT false;
            COMMENT ON COLUMN res_partner.l10n_ro_is_government_institution IS
            'Romania - Is Government Institution';
            """
        )
