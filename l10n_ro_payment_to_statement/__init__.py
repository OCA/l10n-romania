from . import models


def _set_auto_auto_statement(cr, registry):
    """This post-init-hook will update all existing sale.order.line"""
    cr.execute(
        """
        UPDATE account_journal
        SET l10n_ro_auto_statement = True
        WHERE type  = 'cash';"""
    )
