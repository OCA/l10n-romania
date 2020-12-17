# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'Romania - Payroll Application',
    'summary': 'Romania - Payroll Application',
    'version': '11.0.1.0.0',
    'category': 'Localization',
    'author': 'Forest and Biomass Romania, '
              'OdooERP România S.R.L., '
              'Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/l10n-romania',
    'license': 'AGPL-3',
    'depends': [
        'hr_payroll',
        'l10n_ro_hr_contract',
        'l10n_ro_hr_medical_holidays',
        'hr_attendance'],
    'data': [
        # views
        'views/hr_employee_view.xml',
        'views/hr_payroll_view.xml',
        'views/hr_holidays_view.xml',
        'views/hr_meal_vouchers_view.xml',
        'views/hr_wage_history_view.xml',
        # data
        'data/res.partner.csv',
        'data/hr.wage.history.csv',
        'data/hr.contribution.register.csv',
        'data/hr_salary_rule_category.xml',
        'data/hr_salary_rule.xml',
        # report
        'report/hr_meal_vouchers.xml',
        'report/report_meal_vouchers_template.xml',
        # model access
        'security/hr_security.xml',
        'security/ir.model.access.csv'],
    'auto_install': False,
    'development_status': 'Mature',
    'mainteners': [
        'feketemihai',
        'horjarobert'
    ]
}
