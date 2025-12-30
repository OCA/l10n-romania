# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Stock Accounting",
    "version": "19.0.0.7.0",
    "category": "Localization",
    "countries": ["ro"],
    "summary": "Romania - Stock Accounting",
    "author": "NextERP Romania,"
    "Dorin Hongu,"
    "Forest and Biomass Romania,"
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": [
        "stock_dropshipping",
        "l10n_ro_stock",
    ],
    "license": "AGPL-3",
    "data": [
        "views/account_account_view.xml",
        "views/product_category_view.xml",
        "views/product_template_view.xml",
        "views/stock_location_view.xml",
        "views/stock_picking_view.xml",
        "views/stock_warehouse_view.xml",
    ],
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["dhongu", "feketemihai"],
}
