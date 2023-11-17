# Copyright (C) 2015-2020 Deltatech
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


{
    "name": "Romania - Payment to Statement",
    "summary": "Add payment to cash statement",
    "version": "16.0.2.4.0",
    "author": "Terrabit," "NextERP Romania," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "category": "Accounting",
    "depends": ["account_accountant", "l10n_ro_config"],
    "license": "AGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "views/account_payment_view.xml",
        "views/account_journal_view.xml",
        "views/account_journal_dashboard_view.xml",
        "views/account_bank_statement_line.xml",
    ],
    # "post_init_hook": "pre_init_hook",
    "development_status": "Mature",
    "maintainers": ["dhongu"],
}
