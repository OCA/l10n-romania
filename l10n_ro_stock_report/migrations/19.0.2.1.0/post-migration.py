from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    _migrate_stock_move(env)
    
def _migrate_stock_move(env):
    openupgrade.logged_query(
        env.cr,
        """
            UPDATE stock_move sm
            SET l10n_ro_second_account_id = 
                (sl.l10n_ro_property_stock_valuation_account_id->>'id')::integer
            FROM stock_location sl, stock_location sld
            WHERE sm.location_id = sl.id
            AND sm.location_dest_id = sld.id
            AND sm.l10n_ro_second_account_id IS NULL
            AND sl.usage = 'internal'
            AND sld.usage = 'internal';
        """
    )