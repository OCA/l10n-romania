from openupgradelib import openupgrade


def migrate(cr, version):
    if not version:
        return

    model_name = "l10n.ro.res.partner.anaf.status"
    table_name = "l10n_ro_res_partner_anaf_status"
    field_name = "date"

    openupgrade.logged_query(
        cr,
        """
        UPDATE ir_ui_view
        SET arch_db = replace(
            arch_db::text,
            '<field name="date"/>\n',
            ''
        )::jsonb
        WHERE id = (
            SELECT res_id
            FROM ir_model_data
            WHERE module = 'l10n_ro_partner_create_by_vat'
            AND name = 'view_partner_anaf_status_form'
        )
        """,
    )

    if openupgrade.column_exists(cr, table_name, field_name):
        openupgrade.rename_columns(
            cr, {table_name: [(field_name, openupgrade.get_legacy_name(field_name))]}
        )

    openupgrade.logged_query(
        cr,
        """
        DELETE FROM ir_model_fields
        WHERE name = %s AND model = %s
    """,
        (field_name, model_name),
    )

    openupgrade.logged_query(
        cr,
        """
        DELETE FROM ir_model_data
        WHERE model = 'ir.model.fields'
          AND name LIKE %s
    """,
        (f"field_{table_name}_{field_name}%",),
    )
