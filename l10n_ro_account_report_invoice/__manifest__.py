# Copyright 2018 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Romania - Invoice Report",
    "summary": "Romania - Invoice Report",
    "version": "13.0.1.1.0",
    "category": "Localization",
    "author": "NextERP Romania," "Odoo Community Association (OCA)",
    "website": "https://odoo-community.org",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["l10n_ro_config"],
    "data": [
        "views/account_invoice_view.xml",
        "views/invoice_report.xml",
        "views/res_config_settings_view.xml",
    ],
}
