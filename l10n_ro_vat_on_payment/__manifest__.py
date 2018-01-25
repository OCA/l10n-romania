# Copyright  2015 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Romania - VAT on Payment',
    'summary': 'Romania - VAT on Payment',
    'version': '11.0.1.0.0',
    'category': 'Localization',
    'author': 'Forest and Biomass Romania, '
              'Odoo Community Association (OCA)',
    'website': 'https://www.forbiom.eu',
    'license': 'AGPL-3',
    'installable': True,
    'data': ['views/res_partner_view.xml',
             'views/account_tax_view.xml',
             'security/ir.model.access.csv',
             'data/res_partner_anaf_cron.xml'],
    'depends': ['account', 'l10n_ro'],
}
