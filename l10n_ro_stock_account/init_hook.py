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


def store_field_l10n_ro_vat_number(cr):
    cr.execute(
        """SELECT column_name
           FROM information_schema.columns
           WHERE table_name='stock_valuation_layer' AND column_name='account_id'"""
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

    logger.info("Computing field l10n_ro_account_id on stock.valuation.leyer")

    # do res.company.init()
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
