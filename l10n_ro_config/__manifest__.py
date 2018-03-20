# Copyright (C) 2015 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Romania - Localization Config',
    'summary': 'Romania - Localization Install and Config Apllications',
    'version': '11.0.1.0.0',
    'category': 'Localization',
    'author': 'Forest and Biomass Romania, '
              'Odoo Community Association (OCA)',
    'website': 'https://www.forbiom.eu',
    'license': 'AGPL-3',
    'installable': True,
    'depends': ['l10n_ro'],
    'data': ['data/res_currency_data.xml',
             'views/res_config_view.xml'],
    'auto_install': True,
}
