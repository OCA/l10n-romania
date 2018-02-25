# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Romania - Extended Addresses',
    'summary': 'Romania - Extended Addresses',
    'version': '11.0.1.0.0',
    'category': 'Localization',
    'author': 'Forest and Biomass Romania, '
              'Odoo Community Association (OCA)',
    'website': 'https://www.forbiom.eu',
    'license': 'AGPL-3',
    'installable': True,
    'depends': ['base_address_extended'],
    'data': [
        'views/res_company_view.xml',
        'views/res_partner_view.xml',
    ],
}
