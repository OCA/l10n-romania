# -*- coding: utf-8 -*-
from openupgradelib import openupgrade

def migrate(cr, version):
    if not version:
        return

    model_name = 'l10n.ro.res.partner.anaf.status'
    table_name = 'l10n_ro_res_partner_anaf_status'
    field_name = 'date'

    # TODO: Fix the id to not be hardcoded
    openupgrade.logged_query(cr, """
       SELECT replace(
            arch_db::text, 
            '<field name=\"date\"/>\n', 
            ''
        )::jsonb
        FROM ir_ui_view
        WHERE id=2777;
    """)

    if openupgrade.column_exists(cr, table_name, field_name):
        openupgrade.rename_columns(cr, {
            table_name: [(field_name, openupgrade.get_legacy_name(field_name))]
        })

    openupgrade.logged_query(cr, """
        DELETE FROM ir_model_fields 
        WHERE name = %s AND model = %s
    """, (field_name, model_name))

    openupgrade.logged_query(cr, """
        DELETE FROM ir_model_data 
        WHERE model = 'ir.model.fields' 
          AND name LIKE %s
    """, (f'field_{table_name}_{field_name}%',))