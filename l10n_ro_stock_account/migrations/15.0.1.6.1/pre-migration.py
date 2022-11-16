# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging
import sys

_logger = logging.getLogger(__name__)


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
    fields_to_rename = [
        (
            "product.category",
            "product_category",
            "hide_stock_in_out_account",
            "l10n_ro_hide_stock_in_out_account",
        ),
        (
            "product.category",
            "product_category",
            "stock_account_change",
            "l10n_ro_stock_account_change",
        ),
        (
            "product.template",
            "product_template",
            "property_stock_valuation_account_id",
            "l10n_ro_property_stock_valuation_account_id",
        ),
        (
            "stock.location",
            "stock_location",
            "property_account_income_location_id",
            "l10n_ro_property_account_income_location_id",
        ),
        (
            "stock.location",
            "stock_location",
            "property_account_expense_location_id",
            "l10n_ro_property_account_expense_location_id",
        ),
        (
            "stock.location",
            "stock_location",
            "property_stock_valuation_account_id",
            "l10n_ro_property_stock_valuation_account_id",
        ),
        (
            "stock.valuation.layer",
            "stock_valuation_layer",
            "valued_type",
            "l10n_ro_valued_type",
        ),
        (
            "stock.valuation.layer",
            "stock_valuation_layer",
            "invoice_line_id",
            "l10n_ro_invoice_line_id",
        ),
        (
            "stock.valuation.layer",
            "stock_valuation_layer",
            "invoice_id",
            "l10n_ro_invoice_id",
        ),
        (
            "stock.valuation.layer",
            "stock_valuation_layer",
            "account_id",
            "l10n_ro_account_id",
        ),
    ]

    for field_to_rename in fields_to_rename:
        try:
            openupgrade.rename_fields(env, [field_to_rename])
        except Exception as e:
            _logger.error(str(e))

    IrModule = env["ir.module.module"]
    IrModule.update_list()

    ro_comps = env["res.company"].search([("l10n_ro_accounting", "=", True)])
    if ro_comps:
        stock_account_notice_module = IrModule.search(
            [("name", "=", "l10n_ro_stock_account_notice")]
        )
        stock_account_notice_module.button_install()
    # Delete views
    view_list = [
        "view_picking_add_notice_form",
        "view_picking_add_notice_tree",
        "view_picking_internal_add_notice_search",
        "stock_picking_kanban",
    ]
    for view in view_list:
        if env.ref("l10n_ro_stock_account." + view, raise_if_not_found=False):
            env.cr.execute(
                "DELETE FROM ir_ui_view WHERE id = %s"
                % env.ref("l10n_ro_stock_account." + view).id
            )
    stock_landed_costs_module = IrModule.search([("name", "=", "stock_landed_costs")])
    if stock_landed_costs_module.state not in (
        "installed",
        "to install",
        "to upgrade",
    ):
        stock_landed_costs_module.button_install()
