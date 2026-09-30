# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Recompute the stored valuation accounts of the done moves.

    The accounts were chosen on the sign of the move value, which is always
    positive in 19.0, so outputs from a location with its own valuation
    account kept the category account and the storage sheet showed them on
    the wrong account.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    moves = env["stock.move"].search([("state", "=", "done")])
    _logger.info("Recompute the Romanian valuation accounts of %s moves", len(moves))
    moves._compute_account()
    moves.flush_recordset(["l10n_ro_account_id", "l10n_ro_transfer_account_id"])
