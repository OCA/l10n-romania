# Copyright (C) 2017 FOREST AND BIOMASS ROMANIA SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Romania - Employee Contracts',
    'summary': 'Romania  - Employee Contracts',
    'version': '11.0.1.0.0',
    'category': 'Localization',
    'author': 'Forest and Biomass Romania, '
              'Odoo Community Association (OCA)',
    'website': 'https://www.forbiom.eu',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'depends': ['hr_contract'],
    'data': [
        'data/hr.insurance.type.csv',
        'views/hr_contract_view.xml',
        'security/ir.model.access.csv'],
    'auto_install': False,
}
