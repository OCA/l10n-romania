# ©  2008-2018 Fekete Mihai <mihai.fekete@forbiom.eu>
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details
{
    "name": "Romania - Stock Accounting",
    "version": "13.0.1.0.0.",
    "category": "Localization",
    "summary": "Romania - stock account",
    "author": "FOREST AND BIOMASS SERVICES ROMANIA, Terrabit",
    "website": "http://www.forbiom.eu",
    "depends": [
        "stock_account",
        "sale_stock",
        "purchase_stock",
        "l10n_ro_config",
        "l10n_ro_stock",
        "date_range",
    ],
    "license": "AGPL-3",
    "data": [
        "views/stock_move_view.xml",
        "views/stock_location_view.xml",
        "views/product_view.xml",
        "views/product_category.xml",
        "views/account_move_view.xml",
        "views/stock_picking_view.xml",
        "views/stock_inventory.xml",
    ],
    "installable": True,
    "active": False,
}
