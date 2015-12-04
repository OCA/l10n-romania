# -*- coding: utf-8 -*-
# ©  2015 Forest and Biomass Services Romania
# See README.rst file on addons root folder for license details

{
    'name': 'Romania - Siruta',
    'summary': 'Romania - Siruta',
    'version': '8.0.1.0.0',
    'category': 'Localization',
    'author': 'Forest and Biomass Services Romania, '
              'Odoo Community Association (OCA)',
    'website': 'https://www.forbiom.eu',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'depends': ['base', 'l10n_ro'],
    'data': ['views/partner_view.xml',
             'views/siruta_view.xml',
             'security/ir.model.access.csv',
             'data/res.country.zone.csv',
             'data/res.country.state.csv',
             'data/res.country.commune.csv',
             'data/res.country.city.csv',
             ],
    'images': ['static/description/customer.png'],    
}
