# Copyright (C) 2015 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Romania - Siruta',
    'summary': 'Romania - Siruta',
    'version': '11.0.1.0.0',
    'category': 'Localization',
    'author': 'Forest and Biomass Romania, '
              'Odoo Community Association (OCA)',
    'website': 'https://www.forbiom.eu',
    'license': 'AGPL-3',
    'installable': True,
    'depends': ['base', 'base_address_city', 'contacts', 'l10n_ro'],
    'data': ['views/partner_view.xml',
             'views/siruta_view.xml',
             'security/ir.model.access.csv',
             ],
    'demo': ['demo/demo_siruta.xml'],
    'images': ['static/description/customer.png',
               'static/description/address.png']
}
