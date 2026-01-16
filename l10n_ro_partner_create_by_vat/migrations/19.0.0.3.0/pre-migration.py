# -*- coding: utf-8 -*-
from openupgradelib import openupgrade

def migrate(cr, version):
    if not version:
        return

    model_name = 'l10n.ro.res.partner.anaf.status'
    table_name = 'l10n_ro_res_partner_anaf_status'
    field_name = 'date'

    # Drop ref for XML
    openupgrade.logged_query(cr, """
        UPDATE ir_ui_view 
        SET arch_db = regexp_replace(arch_db::text, '<field[^>]*name=[''"]' || %s || '[''"][^>]*/>', '', 'g')::jsonb
        WHERE model = %s AND arch_db::text LIKE %s
    """, (field_name, model_name, f'%{field_name}%'))

    # Drop field from db Odoo
    openupgrade.logged_query(cr, """
        DELETE FROM ir_model_fields 
        WHERE name = %s AND model = %s
    """, (field_name, model_name))

    # Case rename column
    # Folosim utilitarul openupgrade pentru a verifica și redenumi coloana safe
    if openupgrade.column_exists(cr, table_name, field_name):
        openupgrade.rename_columns(cr, {
            table_name: [(field_name, 'date_old')]
        })

    # Update order model
    openupgrade.logged_query(cr, """
        UPDATE ir_model 
        SET order_view = 'start_date desc' 
        WHERE model = %s AND order_view LIKE '%%date%%'
    """, (model_name,))

    # Clear ref for all External ID
    openupgrade.logged_query(cr, """
        DELETE FROM ir_model_data 
        WHERE model = 'ir.model.fields' 
          AND name = %s 
          AND module = 'l10n_ro_anaf_status'
    """, (f'field_{table_name}_{field_name}',))