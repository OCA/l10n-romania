# ©  2018 Deltatech
# See README.rst file on addons root folder for license details


{
    "name": "Romania - Payment to Statement",
    "summary": "Add payment to cash statement",
    "version": "15.0.2.1.0",
    "author": "Terrabit," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "category": "Accounting",
    "depends": ["account", "l10n_ro_config"],
    "license": "AGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "views/account_payment_view.xml",
        "views/account_journal_view.xml",
        "views/account_journal_dashboard_view.xml",
    ],
    "development_status": "Mature",
    "maintainers": ["dhongu"],
}
