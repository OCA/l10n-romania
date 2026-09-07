# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Stock Accounting Retail (Marfa in Magazin)",
    "version": "19.0.2.0.0",
    "category": "Localization",
    "countries": ["ro"],
    "summary": "Romania - Retail merchandise accounting "
    "(371 Marfuri, 378 Adaos comercial, 4428 TVA neexigibila)",
    "author": "NextERP Romania,Dakai Soft SRL,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": [
        "l10n_ro_stock_account",
    ],
    "license": "AGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "views/stock_warehouse_view.xml",
        "views/stock_location_view.xml",
        "views/product_category_view.xml",
        "views/product_template_view.xml",
        "views/res_config_settings_view.xml",
        "views/retail_markup_line_view.xml",
        "wizard/retail_opening_balance_view.xml",
    ],
    "installable": True,
    "auto_install": False,
    "development_status": "Mature",
    "maintainers": ["feketemihai", "adrian-dks"],
}
