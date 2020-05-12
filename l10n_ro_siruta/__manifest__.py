# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Romania - Siruta',
    'category': 'Localization',
    'summary': 'Romania - Siruta',
    'depends': ['base', 'base_address_city', 'contacts', 'l10n_ro'],
    'data': ['views/partner_view.xml',
             'views/siruta_view.xml',
             'security/ir.model.access.csv',
             ],
    'demo': ['demo/demo_siruta.xml'],
    'images': ['static/description/customer.png',
               'static/description/address.png'],
    'license': 'AGPL-3',
    'version': '11.0.1.0.0',
    'author': 'NextERP Romania,'
              'Forest and Biomass Romania,'
              'Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/l10n-romania',
    'installable': True,
    'development_status': 'Mature',
    'maintainers': ['feketemihai'],
}
