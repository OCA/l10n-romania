# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Stock Accounting",
    "version": "16.0.1.23.1",
    "category": "Localization",
    "summary": "Romania - Stock Accounting",
    "author": "NextERP Romania,"
    "Dorin Hongu,"
    "Forest and Biomass Romania,"
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": [
        "l10n_ro_stock_account_determination",
        "l10n_ro_stock_account_landed_cost",
        "l10n_ro_stock_account_tracking",
    ],
    "license": "AGPL-3",
    "data": [
        "wizard/stock_picking_return_views.xml",
        "wizard/stock_valuation_layer_revaluation_views.xml",
    ],
    "pre_init_hook": "pre_init_hook",
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["dhongu", "feketemihai"],
}
