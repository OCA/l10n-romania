# ©  2008-2020 Fekete Mihai <mihai.fekete@forbiom.eu>
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details
{
    "name": "Romania - Stock Accounting",
    "version": "13.0.1.0.0",
    "category": "Localization",
    "summary": "Romania - stock account",
    "author": "NextERP Romania,"
    "Dorin Hongu,"
    "Forest and Biomass Romania,"
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": [
        "stock_account",
        "sale_stock",
        "purchase_stock",
        # "l10n_ro_config",
        "l10n_ro",
        "l10n_ro_stock",
    ],
    "license": "AGPL-3",
    "data": ["views/res_config_view.xml", "views/stock_picking_view.xml"],
    "installable": True,
    "maintainers": ["dhongu"],
}
