# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Romania - Account Period Closing',
    'summary': 'Romania - Account Period Closing',
    'version': '11.0.1.0.0',
    'category': 'Localization',
    'author': 'Forest and Biomass Romania, '
              'Odoo Community Association (OCA)',
    'website': 'https://www.forbiom.eu',
    'license': 'AGPL-3',
    'installable': True,
    'depends': ['account', 'date_range'],
    'data': [
        'views/account_period_close_view.xml',
        'wizards/wizard_account_period_closing_view.xml',
        'security/account_security.xml',
        'security/ir.model.access.csv',
    ],
}
