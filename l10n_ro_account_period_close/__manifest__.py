# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Romania - Account Period Closing",
    "category": "Localization",
    "summary": "Romania - Account Period Closing",
    "depends": ["l10n_ro_config"],
    "data": [
        "views/account_period_close_view.xml",
        "wizards/wizard_account_period_closing_view.xml",
        "security/account_security.xml",
        "security/ir.model.access.csv",
    ],
    "license": "AGPL-3",
    "version": "14.0.3.4.0",
    "author": "NextERP Romania,"
    "Forest and Biomass Romania,"
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "installable": True,
    "development_status": "Mature",
    "external_dependencies": {"python": ["python-dateutil"]},
    "maintainers": ["feketemihai"],
}
