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
            arch_db, 
            '<field[^>]+name=' || quote_literal(%s) || '[^>]*/>', 
            '', 
            'g'
        )
        WHERE arch_db LIKE %s
    """, (field_name, f'%name="{field_name}"%'))

    if openupgrade.column_exists(cr, table_name, field_name):
        openupgrade.rename_columns(cr, {
            table_name: [(field_name, openupgrade.get_legacy_name(field_name))]
        })

    openupgrade.logged_query(cr, """
        DELETE FROM ir_model_fields 
        WHERE name = %s AND model = %s
    """, (field_name, model_name))