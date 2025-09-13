# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade


def migrate(cr, version):
    if not version:
        return

    if not openupgrade.column_exists(
        cr, "stock_valuation_layer", "l10n_ro_location_eval_id"
    ):
        # initializare svl.l10n_ro_location_eval_id
        openupgrade.logged_query(
            cr,
            """
            ALTER TABLE stock_valuation_layer
            ADD COLUMN l10n_ro_location_eval_id integer""",
        )

        # setez l10n_ro_location_eval_id doar pe svl-urile cu quantity diferit de 0
        # apoi svl-urile cu quantity = 0 din svl.stock_valuation_layer_id
        openupgrade.logged_query(
            cr,
            """
            UPDATE stock_valuation_layer
            SET l10n_ro_location_eval_id = CASE
                    WHEN quantity > 0 THEN l10n_ro_location_dest_id
                    WHEN quantity < 0 THEN l10n_ro_location_id
                END
            WHERE quantity != 0;
            """,
        )

        # valuation-uri landed cost
        openupgrade.logged_query(
            cr,
            """
            UPDATE stock_valuation_layer svl_lc
            SET l10n_ro_location_eval_id = svl.l10n_ro_location_eval_id
            FROM stock_valuation_layer svl
            WHERE svl_lc.stock_valuation_layer_id = svl.id AND svl_lc.quantity = 0;
            """,
        )
