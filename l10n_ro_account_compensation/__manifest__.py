# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Account Compensation",
    "summary": "Compensate partners debits and credits",
    "version": "13.0.1.0.0",
    "category": "Accounting & Finance",
    "sequence": 4,
    "author": "NextERP Romania S.R.L.,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "license": "AGPL-3",
    "depends": ["account"],
    "data": [
        # views
        "views/account_compensation_view.xml",
        # model access
        "security/ir.model.access.csv",
        "security/account_compensation_security.xml",
    ],
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
}
