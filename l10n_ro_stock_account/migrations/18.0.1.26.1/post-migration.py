# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Re-attribute the valuation account on zero-value layers.

    Before this version ``_compute_account`` picked the source/destination
    valuation account based on the *value* sign. Zero-value moves (e.g. a
    100% discounted / free product) have value == 0 on every layer, so both
    the out-leg and the in-leg ended up on the category default account,
    leaving residual quantities on the per-account stock card. The compute
    now keys on the *quantity* sign, so we recompute the stored
    ``l10n_ro_account_id`` for the historical zero-value layers to fix the
    stock card retroactively.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    layers = env["stock.valuation.layer"].search([("value", "=", 0)])
    layers = layers.filtered(lambda sv: sv.stock_move_id.is_l10n_ro_record)
    if not layers:
        return
    _logger.info(
        "l10n_ro_stock_account: recomputing l10n_ro_account_id "
        "for %s zero-value layers",
        len(layers),
    )
    layers.invalidate_recordset(["l10n_ro_account_id"])
    layers._compute_account()
    layers.flush_recordset(["l10n_ro_account_id"])
