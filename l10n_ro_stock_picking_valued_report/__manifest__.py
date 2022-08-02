# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Stock Picking Report",
    "version": "14.0.1.0.0",
    "category": "Localization",
    "summary": "Romania -  Stock Picking Report",
    "author": "NextERP Romania," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": [
        "sale_stock",
        "purchase_stock",
        "l10n_ro_stock_account",
        "stock_landed_costs",
    ],
    "excludes": ["stock_picking_report_valued"],
    "license": "AGPL-3",
    "data": [
        "report/stock_picking_report_valued.xml",
    ],
    "installable": True,
    "maintainers": ["feketemihai"],
}
