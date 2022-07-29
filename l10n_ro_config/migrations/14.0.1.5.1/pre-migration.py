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
                "use_romanian_accounting",
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
    ]
    openupgrade.delete_records_safely_by_xml_id(env, views)
