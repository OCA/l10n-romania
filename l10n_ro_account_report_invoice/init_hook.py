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

    The pre init script writes the inverse currency rate to the
    l10n_ro_currency_rate so that it is not computed by the install.

    """
    store_field_l10n_ro_currency_rate(cr)


def store_field_l10n_ro_currency_rate(cr):
    # pylint: disable=sql-injection
    cr.execute(
        """SELECT column_name
           FROM information_schema.columns
           WHERE table_name='account_move' AND column_name='l10n_ro_currency_rate'"""
    )
    if not cr.fetchone():
        cr.execute(
            """
            ALTER TABLE account_move ADD COLUMN l10n_ro_currency_rate numeric;
            COMMENT ON COLUMN account_move.l10n_ro_currency_rate IS 'Ro Currency Rate';
            """
        )

        logger.info("Computing field l10n_ro_currency_rate on account.move")
        cr.execute(
            """
            select id from res_country where code = 'RO';
            """
        )
        ro_country = cr.fetchone()
        if ro_country:
            cr.execute(
                """
                SELECT res_company.id
                FROM res_company
                LEFT JOIN res_partner partner ON partner.id = res_company.partner_id
                WHERE partner.country_id = %s;
                """
                % ro_country
            )
            ro_companies = cr.fetchall()
            if ro_companies:
                ro_companies = [x[0] for x in ro_companies]
                cr.execute(
                    r"""
                    WITH currency_rate
                    (currency_id, company_id, rate, date_start, date_end) AS (
                        SELECT
                            r.currency_id,
                            COALESCE(r.company_id, c.id) as company_id,
                            r.rate,
                            r.name AS date_start,
                            (SELECT name FROM res_currency_rate r2
                            WHERE r2.name > r.name AND
                                r2.currency_id = r.currency_id AND
                                (r2.company_id is null or r2.company_id = c.id)
                            ORDER BY r2.name ASC
                            LIMIT 1) AS date_end
                        FROM res_currency_rate r
                        JOIN res_company c ON (r.company_id is null or r.company_id = c.id)
                    )
                    UPDATE account_move acc_move
                    SET l10n_ro_currency_rate = round(1 / coalesce(cr.rate, 1),4)::numeric
                    FROM currency_rate cr
                    WHERE acc_move.company_id in %(ids)s AND
                        (cr.currency_id = acc_move.currency_id AND
                        cr.date_start <= COALESCE(acc_move.invoice_date, acc_move.date) AND
                        (cr.date_end IS NULL OR
                            cr.date_end > COALESCE(acc_move.invoice_date, acc_move.date)) AND
                        (acc_move.company_id = cr.company_id OR cr.company_id is Null));
                    """,
                    {"ids": tuple(ro_companies)},
                )
            cr.execute(
                r"""
                UPDATE account_move acc_move
                SET l10n_ro_currency_rate = 1
                WHERE acc_move.l10n_ro_currency_rate is Null;
                """
            )
