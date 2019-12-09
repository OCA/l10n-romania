# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Romania - Account Trial Balance Report',
    'category': 'Localization',
    'summary': 'Romania - Account Trial Balance Report',
    'depends': ['account', 'account_financial_report', 'l10n_ro'],
    'data': [
        "views/layouts.xml",
        "views/report_template.xml",
        "views/report_trial_balance.xml",
        "views/trial_balance.xml",
        "views/trial_balance_view.xml",
        "wizards/trial_balance_wizard_view.xml",
    ],
    'license': 'AGPL-3',
    'version': '11.0.1.0.0',
    'author': 'OdooERP Romania,'
              'Forest and Biomass Romania,'
              'Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/l10n-romania',
    'installable': True,
    'development_status': 'Mature',
    'maintainers': ['feketemihai'],
}
