# Copyright (C) 2025 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Stock Picking Valued Report",
    "version": "18.0.0.2.0",
    "category": "Localization",
    "summary": "Romania -  Stock Picking Valued Report",
    "author": "NextERP Romania," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": ["l10n_ro_stock_account", "l10n_ro_stock_account_landed_cost"],
    "excludes": ["stock_picking_report_valued"],
    "license": "AGPL-3",
    "data": [
        "report/stock_picking_report_valued.xml",
    ],
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
}
