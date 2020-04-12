# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# @author -  Fekete Mihai <feketemihai@gmail.com>, Tatár Attila <atta@nvm.ro>
# Copyright (C) 2019 OdooERP Romania (https://odooerpromania.ro)

{
    "name": "Romania - Account Reports",
    "version": "0.1",
    "author": "Fekete Mihai (OdooERP Romania SRL)",
    "website": "https://www.odooerpromania.ro",
    'category': 'Accounting/Localizations',
    'sequence': 21,
    "depends": ['account','l10n_ro',
        'date_range', 
#        'account_vat_on_payment',
#        'l10n_ro_invoice_line_not_deductible',
    ],

    "description": """
Romania  - Accounting Reports
------------------------------------------


    """,

    'data': [
           'report/report_paperformat.xml',
           'report/report_sale.xml',
           'wizard/select_report_sale_purchase_view.xml',
           ],
    'installable': True,
    'auto_install': False,
}
