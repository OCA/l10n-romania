# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Stock Accounting",
    "version": "17.0.1.8.0",
    "category": "Localization",
    "countries": ["ro"],
    "summary": "Romania - Stock Accounting",
    "author": "NextERP Romania,"
    "Dorin Hongu,"
    "Forest and Biomass Romania,"
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": [
        "sale_stock",
        "purchase_stock",
        "stock_dropshipping",
        "l10n_ro_config",
        "l10n_ro_stock",
    ],
    "license": "AGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "views/account_account_view.xml",
        "views/product_category_view.xml",
        "views/product_template_view.xml",
        "views/stock_location_view.xml",
        # "views/stock_picking_view.xml",
        "views/stock_valuation_layer_views.xml",
    ],
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["dhongu", "feketemihai"],
}
