# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Romania - Account Currency Reevaluation',
    'summary': 'Romania - Account Currency Reevaluation',
    'version': '11.0.1.0.0',
    'category': 'Localization',
    'author': 'Forest and Biomass Romania, '
              'Odoo Community Association (OCA)',
    'website': 'https://www.forbiom.eu',
    'license': 'AGPL-3',
    'installable': True,
    'depends': ['account'],
    'data': ['views/account_view.xml',
             'wizard/wizard_currency_revaluation_view.xml'],
}
