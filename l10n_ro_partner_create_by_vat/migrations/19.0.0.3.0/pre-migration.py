# -*- coding: utf-8 -*-
from openupgradelib import openupgrade

def migrate(cr, version):
    if not version:
        return

    model_name = 'l10n.ro.res.partner.anaf.status'
    table_name = 'l10n_ro_res_partner_anaf_status'
    field_name = 'date'

    openupgrade.logged_query(cr, """
        UPDATE ir_ui_view 
        SET arch_db = regexp_replace(
            arch_db::text, 
            '<field[^>]+name=[''"]' || %s || '[''"][^>]*/>', 
            '', 
            'g'
        )::jsonb
        WHERE arch_db::text LIKE %s
    """, (field_name, f'%name="{field_name}"%'))

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