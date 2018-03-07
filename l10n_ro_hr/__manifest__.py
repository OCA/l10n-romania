# Copyright (C) 2017 FOREST AND BIOMASS ROMANIA SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


{
    'name': 'Romania - Human Resources',
    'summary': 'Romania  - Human Resources',
    'version': '11.0.1.0.0',
    'category': 'Localization',
    'author': 'Forest and Biomass Romania, '
              'Odoo Community Association (OCA)',
    'website': 'https://www.forbiom.eu',
    'license': 'AGPL-3',
    'installable': True,
    'depends': ['hr', 'hr_employee_firstname'],
    'external_dependencies': {
        'python': ['stdnum'],
    },
    'data': [
        'views/hr_employee_view.xml',
        'views/res_company_view.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/hr_demo.xml'
    ],
}
