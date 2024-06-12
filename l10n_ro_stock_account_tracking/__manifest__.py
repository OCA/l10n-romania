# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Stock Accounting tracking",
    "version": "16.0.1.28.0",
    "category": "Localization",
    "summary": "Romania - Stock Accounting",
    "author": "NextERP Romania,"
    "Dorin Hongu,"
    "Forest and Biomass Romania,"
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": [
        "l10n_ro_stock_account",
    ],
    "license": "AGPL-3",
    "data": ["security/ir.model.access.csv", "views/stock_valuation_layer_views.xml"],
    "installable": True,
    "pre_init_hook": "pre_init_hook",
    "development_status": "Mature",
    "maintainers": ["dhongu", "feketemihai"],
}
