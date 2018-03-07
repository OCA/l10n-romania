# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Romania - D300 Report',
    'summary': 'Romania - D300 Report',
    'version': '11.0.1.0.0',
    'category': 'Localization',
    'author': 'Forest and Biomass Romania, '
              'Odoo Community Association (OCA)',
    'website': 'https://www.forbiom.eu',
    'license': 'AGPL-3',
    'installable': True,
    'depends': [
        'l10n_ro',
        'date_range',
        'report_xlsx'],
    'data': [
        "views/layouts.xml",
        "views/l10n_ro_report_d300.xml",
        "views/l10n_ro_report_d300_template.xml",
        "views/l10n_ro_report_d300_view.xml",
        "views/report_template.xml",
        "wizards/wizard_l10n_ro_report_d300_view.xml",
    ],
    'demo': [
        'demo/account_tax_tags.xml',
        'demo/account_tax_data.xml',
        'demo/account_fiscal_position_data.xml',
        'demo/account_invoice_data.xml',
    ],
}
