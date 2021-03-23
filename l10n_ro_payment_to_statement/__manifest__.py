# ©  2018 Deltatech
# See README.rst file on addons root folder for license details


{
    "name": "Romania - Payment to Statement",
    "summary": "Add payment to cash statement",
    "version": "14.0.1.0.2",
    "author": "Terrabit," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "category": "Accounting",
    "depends": ["account"],
    "license": "AGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "views/account_payment_view.xml",
        "views/account_journal_view.xml",
        "views/account_journal_dashboard_view.xml",
    ],
    "post_init_hook": "_set_auto_auto_statement",
    "development_status": "Mature",
    "maintainers": ["dhongu"],
}
