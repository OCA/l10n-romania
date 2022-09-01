# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import sys


def install(package):
    try:
        __import__(package)
    except Exception:
        import subprocess

        subprocess.call([sys.executable, "-m", "pip", "install", package])


install("openupgradelib")

try:
    from openupgradelib import openupgrade
except ImportError:
    openupgrade = None


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    openupgrade.rename_fields(
        env,
        [
            (
                "account.journal",
                "account_journal",
                "print_report",
                "l10n_ro_print_report",
            ),
            ("res.bank", "res_bank", "print_report", "l10n_ro_print_report"),
            ("sale.agent", "sales_agent", "partner_id", "res_partner_id"),
            ("res.company", "res_company", "romanian_accounting", "l10n_ro_accounting"),
            ("res.company", "res_company", "share_capital", "l10n_ro_share_capital"),
            ("res.company", "res_company", "caen_code", "l10n_ro_caen_code"),
            (
                "res.company",
                "res_company",
                "account_serv_sale_tax_id",
                "l10n_ro_account_serv_sale_tax_id",
            ),
            (
                "res.company",
                "res_company",
                "account_serv_purchase_tax_id",
                "l10n_ro_account_serv_purchase_tax_id",
            ),
            (
                "res.company",
                "res_company",
                "property_vat_on_payment_position_id",
                "l10n_ro_property_vat_on_payment_position_id",
            ),
            (
                "res.company",
                "res_company",
                "property_inverse_taxation_position_id",
                "l10n_ro_property_inverse_taxation_position_id",
            ),
            (
                "res.company",
                "res_company",
                "property_stock_picking_payable_account_id",
                "l10n_ro_property_stock_picking_payable_account_id",
            ),
            (
                "res.company",
                "res_company",
                "property_stock_picking_receivable_account_id",
                "l10n_ro_property_stock_picking_receivable_account_id",
            ),
            (
                "res.company",
                "res_company",
                "property_stock_usage_giving_account_id",
                "l10n_ro_property_stock_usage_giving_account_id",
            ),
            (
                "res.company",
                "res_company",
                "property_stock_picking_custody_account_id",
                "l10n_ro_property_stock_picking_custody_account_id",
            ),
            (
                "res.company",
                "res_company",
                "property_uneligible_tax_account_id",
                "l10n_ro_property_uneligible_tax_account_id",
            ),
            (
                "res.company",
                "res_company",
                "property_stock_transfer_account_id",
                "l10n_ro_property_stock_transfer_account_id",
            ),
            (
                "res.company",
                "res_company",
                "property_trade_discount_received_account_id",
                "l10n_ro_property_trade_discount_received_account_id",
            ),
            (
                "res.company",
                "res_company",
                "property_trade_discount_granted_account_id",
                "l10n_ro_property_trade_discount_granted_account_id",
            ),
            (
                "res.company",
                "res_company",
                "stock_acc_price_diff",
                "l10n_ro_stock_acc_price_diff",
            ),
            (
                "res.company",
                "res_company",
                "property_stock_price_difference_product_id",
                "l10n_ro_property_stock_price_difference_product_id",
            ),
            (
                "res.config.settings",
                "res_config_settings",
                "romanian_accounting",
                "l10n_ro_accounting",
            ),
            (
                "res.config.settings",
                "res_config_settings",
                "share_capital",
                "l10n_ro_share_capital",
            ),
            (
                "res.config.settings",
                "res_config_settings",
                "caen_code",
                "l10n_ro_caen_code",
            ),
            (
                "res.config.settings",
                "res_config_settings",
                "serv_sale_tax_id",
                "l10n_ro_account_serv_sale_tax_id",
            ),
            (
                "res.config.settings",
                "res_config_settings",
                "serv_purchase_tax_id",
                "l10n_ro_account_serv_purchase_tax_id",
            ),
            (
                "res.config.settings",
                "res_config_settings",
                "property_vat_on_payment_position_id",
                "l10n_ro_property_vat_on_payment_position_id",
            ),
            (
                "res.config.settings",
                "res_config_settings",
                "property_inverse_taxation_position_id",
                "l10n_ro_property_inverse_taxation_position_id",
            ),
            (
                "res.config.settings",
                "res_config_settings",
                "property_stock_picking_payable_account_id",
                "l10n_ro_property_stock_picking_payable_account_id",
            ),
            (
                "res.config.settings",
                "res_config_settings",
                "property_stock_picking_receivable_account_id",
                "l10n_ro_property_stock_picking_receivable_account_id",
            ),
            (
                "res.config.settings",
                "res_config_settings",
                "property_stock_usage_giving_account_id",
                "l10n_ro_property_stock_usage_giving_account_id",
            ),
            (
                "res.config.settings",
                "res_config_settings",
                "property_stock_picking_custody_account_id",
                "l10n_ro_property_stock_picking_custody_account_id",
            ),
            (
                "res.config.settings",
                "res_config_settings",
                "property_uneligible_tax_account_id",
                "l10n_ro_property_uneligible_tax_account_id",
            ),
            (
                "res.config.settings",
                "res_config_settings",
                "property_stock_transfer_account_id",
                "l10n_ro_property_stock_transfer_account_id",
            ),
            (
                "res.config.settings",
                "res_config_settings",
                "property_trade_discount_received_account_id",
                "l10n_ro_property_trade_discount_received_account_id",
            ),
            (
                "res.config.settings",
                "res_config_settings",
                "property_trade_discount_granted_account_id",
                "l10n_ro_property_trade_discount_granted_account_id",
            ),
            (
                "res.config.settings",
                "res_config_settings",
                "stock_acc_price_diff",
                "l10n_ro_stock_acc_price_diff",
            ),
            (
                "res.config.settings",
                "res_config_settings",
                "property_stock_price_difference_product_id",
                "l10n_ro_property_stock_price_difference_product_id",
            ),
            ("res.partner", "res_partner", "vat_subjected", "l10n_ro_vat_subjected"),
            ("res.partner", "res_partner", "vat_number", "l10n_ro_vat_number"),
            ("res.partner", "res_partner", "caen_code", "l10n_ro_caen_code"),
            ("res.users", "res_users", "vat_number", "l10n_ro_vat_number"),
            ("res.users", "res_users", "caen_code", "l10n_ro_caen_code"),
            ("res.users", "res_users", "vat_subjected", "l10n_ro_vat_subjected"),
            ("res.users", "res_users", "vat_on_payment", "l10n_ro_vat_on_payment"),
        ],
    )
    openupgrade.drop_columns(
        env.cr,
        [
            ("res_config_settings", "module_l10n_ro_dvi"),
            ("res_config_settings", "module_l10n_ro_stock_picking_report_store"),
            ("res_config_settings", "module_l10n_ro_stock_account_store"),
            ("res_config_settings", "module_l10n_ro_intrastat"),
            ("res_config_settings", "module_l10n_ro_account_report_trial_balance"),
        ],
    )

    views = [
        "l10n_ro_config.res_config_settings_view_form",
        "l10n_ro_config.res_config_settings_account_view_form",
        "l10n_ro_config.view_account_bank_journal_form",
        "l10n_ro_config.view_partner_create_by_vat",
    ]
    openupgrade.delete_records_safely_by_xml_id(env, views)

    env.cr.execute(
        """SELECT column_name
           FROM information_schema.columns
           WHERE table_name='ir_ui_menu' AND column_name='is_l10n_ro_record'"""
    )
    if not env.cr.fetchone():
        env.cr.execute(
            """
            ALTER TABLE ir_ui_menu ADD COLUMN is_l10n_ro_record boolean;
            """
        )

    env.cr.execute(
        """
    DO $$
    DECLARE
        _view_ids int[];
        _view_ids_tmp int[];
    BEGIN
        _view_ids := ARRAY(
            SELECT res_id
            FROM ir_model_data
            WHERE module like 'l10n_ro_%' AND model = 'ir.ui.view');
        _view_ids_tmp := _view_ids;
        LOOP
            _view_ids_tmp := ARRAY(
                SELECT id
                FROM ir_ui_view
                WHERE inherit_id = ANY( _view_ids_tmp));
            EXIT WHEN cardinality(_view_ids_tmp) = 0;
            _view_ids := _view_ids || _view_ids_tmp;
        END LOOP;
        DELETE FROM ir_model_data
        WHERE model = 'ir.ui.view' AND res_id = ANY(_view_ids);
        DELETE FROM ir_ui_view WHERE id = ANY(_view_ids);
    END$$;
    """
    )
