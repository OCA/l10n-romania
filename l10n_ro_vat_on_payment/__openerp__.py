# -*- coding: utf-8 -*-
# ©  2015 Forest and Biomass Services Romania
# See README.rst file on addons root folder for license details

{
    'name': 'Romania - VAT on Payment',
    'summary': 'Romania - VAT on Payment',
    'version': '8.0.1.0.0',
    'category': 'Localization',
    'author': 'Forest and Biomass Services Romania, '
              'Odoo Community Association (OCA)',
    'website': 'https://www.forbiom.eu',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'data': ['views/account_invoice_view.xml',
             'views/res_partner_view.xml',
             'security/ir.model.access.csv',
             'views/res_partner_anaf_cron.xml'],
    'depends': ['account_vat_on_payment'],
    'auto_install': False,
}
