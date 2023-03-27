# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade


def migrate(cr, version):
    if not version:
        return

    if not openupgrade.table_exists(
        cr, "stock_production_lot_stock_valuation_layer_rel"
    ):
        # initlizare svl.lot_ids
        openupgrade.logged_query(
            cr,
            """CREATE TABLE stock_production_lot_stock_valuation_layer_rel
            (stock_valuation_layer_id INTEGER, stock_production_lot_id INTEGER)""",
        )
        openupgrade.logged_query(
            cr,
            """
            INSERT INTO stock_production_lot_stock_valuation_layer_rel (
                stock_valuation_layer_id, stock_production_lot_id)
            SELECT svl.id, sml.lot_id
            FROM stock_valuation_layer svl
            LEFT JOIN stock_move sm ON svl.stock_move_id = sm.id
            LEFT JOIN stock_move_line sml ON sml.move_id = sm.id
            WHERE sml.lot_id != null
            """,
        )

    if not openupgrade.column_exists(
        cr, "stock_valuation_layer", "l10n_ro_stock_move_line_id"
    ):
        # initializare svl.l10n_ro_stock_move_line_id
        openupgrade.logged_query(
            cr,
            """
            ALTER TABLE stock_valuation_layer
            ADD COLUMN l10n_ro_stock_move_line_id integer""",
        )
        openupgrade.logged_query(
            cr,
            """
            UPDATE stock_valuation_layer svl
            SET l10n_ro_stock_move_line_id = sub.sml_id
            FROM (
                SELECT svl.id as svl_id, min(sml.id) as sml_id
                FROM stock_valuation_layer svl
                LEFT JOIN stock_move sm on sm.id = svl.stock_move_id
                LEFT JOIN stock_move_line sml on sml.move_id = sm.id
                GROUP BY svl.id
            ) as sub
            WHERE sub.svl_id = svl.id
            """,
        )

    if not openupgrade.column_exists(
        cr, "stock_valuation_layer", "l10n_ro_location_id"
    ):
        # initializare svl.l10n_ro_location_id, svl.l10n_ro_location_dest_id
        openupgrade.logged_query(
            cr,
            """
            ALTER TABLE stock_valuation_layer
            ADD COLUMN l10n_ro_location_id integer""",
        )
        openupgrade.logged_query(
            cr,
            """
            ALTER TABLE stock_valuation_layer
            ADD COLUMN l10n_ro_location_dest_id integer""",
        )
        openupgrade.logged_query(
            cr,
            """
            WITH sub as (
                SELECT
                    svl.id as svl_id,
                    CASE WHEN count(sml.id) = 1
                        THEN min(sml.location_id)
                        ELSE min(sm.location_id)
                    END as location_id,
                    CASE WHEN count(sml.id) = 1
                        THEN min(sml.location_dest_id)
                        ELSE min(sm.location_dest_id)
                    END as location_dest_id
                FROM stock_valuation_layer svl
                LEFT JOIN stock_move sm on sm.id = svl.stock_move_id
                LEFT JOIN stock_move_line sml on sml.move_id = sm.id
                GROUP BY svl.id
            )

            UPDATE stock_valuation_layer svl SET
                l10n_ro_location_id = sub.location_id,
                l10n_ro_location_dest_id = sub.location_dest_id
            FROM sub
            WHERE sub.svl_id = svl.id""",
        )
