# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

logger = logging.getLogger(__name__)


def pre_init_hook(cr):
    """
    The objective of this hook is to speed up the installation
    of the module on an existing Odoo instance.

    Without this script, if a database has a few hundred thousand
    partners, which is not unlikely, the update will take
    at least a few hours.

    The pre init script writes the digits from vat fields to the
    l10n_ro_vat_number so that it is not computed by the install.

    """
    store_field_l10n_ro_vat_number(cr)
    store_svl_lot_and_locations(cr)


def store_field_l10n_ro_vat_number(cr):
    cr.execute(
        """SELECT column_name
           FROM information_schema.columns
           WHERE table_name='stock_valuation_layer' AND column_name='l10n_ro_account_id'"""
    )
    if not cr.fetchone():
        cr.execute(
            """
            ALTER TABLE stock_valuation_layer ADD COLUMN l10n_ro_account_id integer;
            COMMENT ON COLUMN stock_valuation_layer.l10n_ro_account_id IS 'SVL Account';
            """
        )
        cr.execute(
            """
            ALTER TABLE stock_valuation_layer ADD
                CONSTRAINT stock_valuation_layer_l10n_ro_account_id_fkey
                FOREIGN KEY (l10n_ro_account_id)
                REFERENCES account_account (id) MATCH SIMPLE
                ON UPDATE NO ACTION
                ON DELETE RESTRICT;
            """
        )

        logger.info("Computing field l10n_ro_account_id on stock.valuation.layer")

        # do res.company.init()

        cr.execute(
            """SELECT column_name
            FROM information_schema.columns
            WHERE table_name='res_company' AND column_name='l10n_ro_accounting'"""
        )

        if not cr.fetchone():
            cr.execute(
                """
                ALTER TABLE res_company ADD COLUMN l10n_ro_accounting boolean;
                """
            )

        cr.execute(
            """
            UPDATE res_company comp
            SET l10n_ro_accounting = true
            FROM res_partner rp
            WHERE comp.partner_id = rp.id and
                rp.country_id in (SELECT res_id FROM ir_model_data
                                    WHERE model = 'res.country' and
                                        name = 'ro' and module='base'
                                );
        """
        )

        cr.execute(
            """
            WITH prepared_data as (
            SELECT
                svl.id as svl_id,
                COALESCE(
                    aml_for_loop.account,
                    replace(irp_ctg.value_reference, 'account.account,', '')::integer
                ) as account_id

                from stock_valuation_layer svl
                left join stock_move sm on svl.stock_move_id = sm.id
                left join product_product pp on pp.id = svl.product_id
                left join product_template ptmpl on ptmpl.id = pp.product_tmpl_id

                left join ir_property irp_ctg on
                    irp_ctg.res_id = CONCAT('product.category,', ptmpl.categ_id)
                    and sm.company_id = irp_ctg.company_id
                    and irp_ctg.name = 'property_stock_valuation_account_id'

                left join (
                    select sub.move_id, sub.balance, sub.account
                    from (
                            select
                                am.id as move_id,
                                aa.code,
                                aml.balance,
                                COALESCE(
                                    CASE
                                        WHEN (aa.code like '2%' or aa.code like '3%')
                                        THEN aml.account_id
                                        ELSE null
                                    END) account,
                                row_number() over (partition by am.id order by aa.code) as rnum
                                from account_move am
                                left join account_move_line aml on aml.move_id = am.id
                                left join account_account aa on aa.id = aml.account_id
                                group by am.id, aa.code, aml.account_id, aml.balance
                                order by am.id, aa.code
                    ) as sub where sub.account is not null and sub.rnum = 1
                    group by sub.move_id, sub.account, sub.balance

                ) as aml_for_loop on
                    aml_for_loop.move_id = svl.account_move_id
                    and round(aml_for_loop.balance - svl.value, 2) = 0

                left join res_company comp on sm.company_id = comp.id

                where comp.l10n_ro_accounting = true
            order by svl.id
            )

            UPDATE stock_valuation_layer svl
            SET l10n_ro_account_id = prepared_data.account_id
            FROM prepared_data
            WHERE svl.id = prepared_data.svl_id;
            """
        )

    # initializare valued_type

    cr.execute(
        """SELECT column_name
           FROM information_schema.columns
           WHERE table_name='stock_valuation_layer' AND column_name='l10n_ro_valued_type'"""
    )
    if not cr.fetchone():
        cr.execute(
            """
            ALTER TABLE stock_valuation_layer ADD COLUMN l10n_ro_valued_type varchar;
            """
        )

        cr.execute(
            """
        WITH prepared_data as (
        SELECT
            svl.id as svl_id,
            CASE
                WHEN sm2.in_out_type = 'in' and
                     sl_src.usage = 'supplier'
                     THEN 'reception'
                WHEN sm2.in_out_type = 'out' and
                     sl_dest.usage = 'supplier'
                     THEN 'reception_return'
                WHEN sm2.in_out_type = 'out' and
                     sl_dest.usage = 'customer'
                     THEN 'delivery'
                WHEN sm2.in_out_type = 'in' and
                     sl_src.usage = 'customer'
                     THEN 'delivery_return'
                WHEN sl_src.usage = 'inventory' and
                     sl_dest.usage = 'internal'
                     THEN 'plus_inventory'
                WHEN sl_src.usage = 'internal' and
                     sl_dest.usage = 'inventory'
                     THEN 'minus_inventory'
                WHEN sm2.in_out_type = 'in' and
                     sl_src.usage = 'production' and
                     sm.origin_returned_move_id is null
                     THEN 'production'
                WHEN sm2.in_out_type = 'out' and
                     sl_dest.usage = 'production' and
                     sm.origin_returned_move_id is not null
                     THEN 'production_return'
                WHEN sm2.in_out_type = 'out' and
                     sl_dest.usage = 'consume' and
                     sm.origin_returned_move_id is null
                     THEN 'consumption'
                WHEN sm2.in_out_type = 'in' and
                     sl_src.usage = 'consume' and
                     sm.origin_returned_move_id is not null
                     THEN 'consumption_return'
                WHEN sl_dest.usage = 'internal' and
                     sl_src.usage = 'internal'
                     THEN 'internal_transfer'
                WHEN sm2.in_out_type = 'in' and
                     sl_dest.usage = 'usage_giving'
                     THEN 'usage_giving'
                WHEN sm2.in_out_type = 'out' and
                     sl_src.usage = 'usage_giving'
                     THEN 'usage_giving_return'
                ELSE null
            END as valued_type

            FROM stock_valuation_layer svl

            left join stock_move sm on svl.stock_move_id = sm.id

            left join (
                SELECT sm.id as move_id,
                CASE
                    WHEN sl_src1.usage != 'internal' and sl_dest1.usage = 'internal' THEN 'in'
                    WHEN sl_src1.usage = 'internal' and sl_dest1.usage != 'internal' THEN 'out'
                    ELSE null
                END as in_out_type

                FROM stock_move sm
                left join stock_location sl_src1 on sm.location_id = sl_src1.id
                left join stock_location sl_dest1 on sm.location_dest_id = sl_dest1.id
            ) as sm2 on sm2.move_id = sm.id and sm2.in_out_type is not null

            left join stock_location sl_src on sm.location_id = sl_src.id

            left join stock_location sl_dest on sm.location_dest_id = sl_dest.id

            left join res_company comp on sm.company_id = comp.id

            where comp.l10n_ro_accounting = true
        order by svl.id
        )

        UPDATE stock_valuation_layer svl
        SET l10n_ro_valued_type = prepared_data.valued_type
        FROM prepared_data
        WHERE svl.id = prepared_data.svl_id;
        """
        )


def store_svl_lot_and_locations(cr):
    # initializare svl.lot_ids
    cr.execute(
        """SELECT column_name
           FROM information_schema.columns
           WHERE table_name='stock_production_lot_stock_valuation_layer_rel'"""
    )
    if not cr.fetchone():
        cr.execute(
            """CREATE TABLE stock_production_lot_stock_valuation_layer_rel
            (stock_valuation_layer_id INTEGER, stock_production_lot_id INTEGER)""",
        )
        cr.execute(
            """
            INSERT INTO stock_production_lot_stock_valuation_layer_rel (
                stock_valuation_layer_id, stock_production_lot_id)
            SELECT svl.id, sml.lot_id
            FROM stock_valuation_layer svl
            LEFT JOIN stock_move sm ON svl.stock_move_id = sm.id
            LEFT JOIN stock_move_line sml ON sml.move_id = sm.id
            WHERE sml.lot_id is not null
            """,
        )

    # initializare svl.l10n_ro_stock_move_line_id
    cr.execute(
        """SELECT column_name
           FROM information_schema.columns
           WHERE table_name='stock_valuation_layer' AND
           column_name='l10n_ro_stock_move_line_id'"""
    )

    if not cr.fetchone():
        cr.execute(
            """
            ALTER TABLE stock_valuation_layer
            ADD COLUMN l10n_ro_stock_move_line_id integer""",
        )
        cr.execute(
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

    # initializare svl.l10n_ro_location_id, svl.l10n_ro_location_dest_id
    cr.execute(
        """SELECT column_name
           FROM information_schema.columns
           WHERE table_name='stock_valuation_layer' AND column_name='l10n_ro_location_id'"""
    )
    if not cr.fetchone():
        cr.execute(
            """
                ALTER TABLE stock_valuation_layer
                ADD COLUMN l10n_ro_location_id integer""",
        )
        cr.execute(
            """
                ALTER TABLE stock_valuation_layer
                ADD COLUMN l10n_ro_location_dest_id integer""",
        )
        cr.execute(
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
