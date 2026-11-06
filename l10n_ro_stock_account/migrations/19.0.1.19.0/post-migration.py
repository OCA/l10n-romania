import logging

from odoo import SUPERUSER_ID, api
from odoo.tools import split_every

_logger = logging.getLogger(__name__)

BATCH_SIZE = 1000


def migrate(cr, version):
    """Recompute the stored valuation accounts of the done moves.

    The accounts were chosen on the sign of the move value, which is always
    positive in 19.0, so outputs from a location with its own valuation
    account kept the category account and the storage sheet showed them on
    the wrong account.

    Only moves that can change are recomputed: products of a category using
    the location accounts, and moves already carrying a transfer account.
    """
    cr.execute(
        """
        SELECT sm.id
          FROM stock_move sm
          JOIN product_product pp ON pp.id = sm.product_id
          JOIN product_template pt ON pt.id = pp.product_tmpl_id
          JOIN product_category pc ON pc.id = pt.categ_id
         WHERE sm.state = 'done'
           AND (pc.l10n_ro_stock_account_change
                OR sm.l10n_ro_transfer_account_id IS NOT NULL)
         ORDER BY sm.id
        """
    )
    move_ids = [row[0] for row in cr.fetchall()]
    _logger.info("Recompute the Romanian valuation accounts of %s moves", len(move_ids))
    env = api.Environment(cr, SUPERUSER_ID, {})
    fnames = ["l10n_ro_account_id", "l10n_ro_transfer_account_id"]
    for batch_ids in split_every(BATCH_SIZE, move_ids):
        moves = env["stock.move"].browse(batch_ids)
        moves._compute_account()
        moves.flush_recordset(fnames)
        env.invalidate_all()
