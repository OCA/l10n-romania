{
    "name": "Romania - Cache Payment Sequence",
    "summary": "Add Number to cash statement",
    "version": "14.0.1.0.1",
    "author": "Nexterp, Terrabit," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "category": "Accounting",
    "depends": ["account"],
    "license": "AGPL-3",
    "data": [
        "views/account_payment_view.xml",
        "views/account_journal_view.xml",
    ],
    "post_init_hook": "give_initial_sequence_to_payments",
    "development_status": "Mature",
    "maintainers": [],
}
