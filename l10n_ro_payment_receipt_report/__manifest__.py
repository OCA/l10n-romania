# Copyright (C) 2018 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2019 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Romania - Payment Receipt Report",
    "summary": "Romania - Payment Receipt Report",
    "version": "14.0.2.2.0",
    "author": "Terrabit," "NextERP Romania," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "category": "Accounting",
    "depends": ["l10n_ro_payment_to_statement"],
    "license": "AGPL-3",
    "data": [
        "data/report_paperformat.xml",
        "views/payment_receipt_report.xml",
        "views/bank_statement_line_report.xml",
        "views/report_payment_receipt_template.xml",
        "views/report_bank_statement_line_payment_template.xml",
        "views/account_bank_statement_view.xml",
    ],
    "uninstall_hook": "uninstall_hook",
    "development_status": "Mature",
    "maintainers": ["dhongu", "feketemihai"],
}
