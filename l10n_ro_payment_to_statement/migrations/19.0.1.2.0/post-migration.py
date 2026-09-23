# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tools.sql import column_exists

_logger = logging.getLogger(__name__)

LISTED_LINES = 500


def migrate(cr, version):
    """Clean up what the previous way of keeping the cash register left.

    The register used to be built for any journal where a statement of the
    day happened to exist, and the payment held links of its own to that
    statement and to its line. The register is now kept for cash journals
    asking for it, and the links are the ones odoo holds already.

    l10n_ro_statement_id and l10n_ro_statement_line_id are no longer fields of
    account.payment, but their columns are left in the database: they are the
    only way left to tell which line was made out of which payment, which is
    what a cleanup of the lines below needs. A later version drops them.
    """
    if not column_exists(cr, "account_payment", "l10n_ro_statement_line_id"):
        return
    _report_lines_of_journals_without_a_register(cr)
    _stop_offering_a_register_outside_cash(cr)


def _report_lines_of_journals_without_a_register(cr):
    """Tell about the lines this version would not have created.

    They are journal entries of their own, possibly reconciled: deleting
    them is an accounting decision, not something a migration can take.
    """
    cr.execute(
        """
        SELECT j.code, j.type, count(line.id), sum(line.amount),
               array_agg(line.id ORDER BY line.id)
          FROM account_bank_statement_line line
          JOIN account_payment payment
            ON payment.l10n_ro_statement_line_id = line.id
          JOIN account_journal j ON j.id = line.journal_id
         WHERE j.type != 'cash'
            OR COALESCE(j.l10n_ro_auto_statement, FALSE) IS FALSE
         GROUP BY j.code, j.type
         ORDER BY j.code
        """
    )
    rows = cr.fetchall()
    if rows:
        _logger.warning(
            "The links of the payments to their statement lines are kept in "
            "the database, although they are not fields any more, so that the "
            "lines below can still be found and cleaned up."
        )
    for code, journal_type, count, amount, line_ids in rows:
        _logger.warning(
            "Journal %s (%s) holds %s statement line(s) worth %s made out of "
            "payments, which this version would not create. They are left "
            "untouched: check them against the statements of the bank before "
            "deciding what to do with them. Lines: %s",
            code,
            journal_type,
            count,
            amount,
            ", ".join(str(line) for line in line_ids[:LISTED_LINES]),
        )


def _stop_offering_a_register_outside_cash(cr):
    cr.execute(
        """
        UPDATE account_journal SET l10n_ro_auto_statement = FALSE
         WHERE type != 'cash' AND l10n_ro_auto_statement IS TRUE
        """
    )
    if cr.rowcount:
        _logger.info(
            "The cash register was unset on %s journal(s) which are not cash",
            cr.rowcount,
        )
