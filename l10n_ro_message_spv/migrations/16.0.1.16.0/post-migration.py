def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        UPDATE l10n_ro_message_spv
        SET invoice_date = account_move.invoice_date
        FROM account_move
        WHERE l10n_ro_message_spv.invoice_id = account_move.id
        """
    )
