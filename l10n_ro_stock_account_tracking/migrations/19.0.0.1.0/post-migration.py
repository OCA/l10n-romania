from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    _migrate_valuation_tracking(env)


def _migrate_valuation_tracking(env):
    """
    Migrate stock valuation tracking to stock move tracking.
    From table l10n_ro_stock_valuation_layer_tracking to l10n_ro_stock_move_tracking
    svl_src_id.stock_move_id -> src_move_id
    svl_dest_id.stock_move_id -> dest_move_id
    quantity -> quantity
    value -> value
    """
    # Check if the source table exists
    if not openupgrade.table_exists(env.cr, "stock_valuation_layer"):
        return
    # flake8: noqa: E501
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO l10n_ro_stock_move_tracking (src_move_id, dest_move_id, quantity, value)
        SELECT svl_src.stock_move_id AS src_move_id,
               svl_dest.stock_move_id AS dest_move_id,
               svl_track.quantity AS quantity,
               svl_track.value AS value
        FROM l10n_ro_stock_valuation_layer_tracking AS svl_track
        LEFT JOIN stock_valuation_layer AS svl_dest ON svl_track.svl_dest_id = svl_dest.id
        LEFT JOIN stock_valuation_layer AS svl_src ON svl_track.svl_src_id = svl_src.id
        ON CONFLICT DO NOTHING;
        """,
    )
