import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # In 19.0 the l10n_ro_fiscal_position_id field moved from stock.picking.type
    # to stock.warehouse. On databases migrated from 18.0 the old view and column
    # remain and break the validation of any view that inherits the
    # stock.picking.type form. Clean them up before the data is loaded.
    cr.execute(
        """
        DELETE FROM ir_ui_view
         WHERE id IN (
            SELECT res_id FROM ir_model_data
             WHERE module = 'l10n_ro_stock_account'
               AND name = 'view_picking_type_form'
               AND model = 'ir.ui.view'
         )
        """
    )
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'l10n_ro_stock_account'
           AND name = 'view_picking_type_form'
        """
    )
    cr.execute(
        "ALTER TABLE stock_picking_type "
        "DROP COLUMN IF EXISTS l10n_ro_fiscal_position_id"
    )
    _logger.info(
        "l10n_ro_stock_account: removed stale stock.picking.type "
        "l10n_ro_fiscal_position_id view and column"
    )
