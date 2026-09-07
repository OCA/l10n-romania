# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Retail Picking Report (NIR Marfa in Magazin)",
    "version": "19.0.1.0.0",
    "category": "Localization",
    "countries": ["ro"],
    "summary": "Romania - Cost, markup and deferred VAT columns on the "
    "reception note of goods entering a shop",
    "author": "NextERP Romania,Dakai Soft SRL,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": [
        "l10n_ro_stock_account_retail",
        "l10n_ro_stock_picking_valued_report",
    ],
    "license": "AGPL-3",
    "data": [
        "report/stock_picking_report_retail.xml",
    ],
    "installable": True,
    "auto_install": True,
    "development_status": "Mature",
    "maintainers": ["feketemihai", "adrian-dks"],
}
