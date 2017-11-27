# Copyright (C) 2017 FOREST AND BIOMASS ROMANIA SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'Romania - Medical Leaves',
    'summary': 'Romania - Medical Leaves',
    'version': '11.0.1.0.0',
    'category': 'Localization',
    'author': 'Forest and Biomass Romania, '
              'Odoo Community Association (OCA)',
    'website': 'https://www.forbiom.eu',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'depends': [
        'project_timesheet_holidays',
        'hr_holidays_public',
        'l10n_ro_hr'],
    'data': [
        'views/hr_holidays_view.xml',
        'security/ir.model.access.csv'],
    'demo': ['demo/demo.xml'],
    'auto_install': False,
}
