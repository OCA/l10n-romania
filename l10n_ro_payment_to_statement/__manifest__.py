# Copyright (C) 2015-2020 Deltatech
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


{
    "name": "Romania - Payment to Statement",
    "summary": "Add payment to cash statement",
    "version": "14.0.2.5.0",
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
        "views/cash_box_out.xml",
    ],
    "post_init_hook": "_set_auto_auto_statement",
    "development_status": "Mature",
    "maintainers": ["dhongu"],
}
