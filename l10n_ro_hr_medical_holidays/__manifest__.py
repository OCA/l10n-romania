# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Romania - Medical Leaves',
    'category': 'Localization',
    'summary': 'Romania - Medical Leaves',
    'depends': [
        'project_timesheet_holidays',
        'hr_holidays_public',
        'l10n_ro_hr'],
    'data': [
        'views/hr_holidays_view.xml',
        'security/ir.model.access.csv'],
    'demo': ['demo/demo.xml'],
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
