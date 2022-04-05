# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Stock Accounting",
    "version": "14.0.2.5.0",
    "category": "Localization",
    "summary": "Romania - Stock Accounting",
    "author": "NextERP Romania,"
    "Dorin Hongu,"
    "Forest and Biomass Romania,"
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": [
        "stock_account",
        "sale_stock",
        "purchase_stock",
        "l10n_ro_config",
        "l10n_ro_stock",
    ],
    "license": "AGPL-3",
    "data": [
        "views/product_category_view.xml",
        "views/product_template_view.xml",
        "views/stock_location_view.xml",
        "views/stock_picking_view.xml",
        "views/stock_valuation_layer_views.xml",
        "wizard/stock_picking_return_views.xml",
    ],
    "installable": True,
    "maintainers": ["dhongu", "feketemihai"],
}
