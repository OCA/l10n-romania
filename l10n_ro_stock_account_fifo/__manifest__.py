# -*- coding: utf-8 -*-
{
  'name':'Romania stock account fifo',
  'description': """FIFO pe locatii si loturi + Tracking SVL""",
  'version':'14.0',
  'author':'Dakai SOFT',
  'website': "https://github.com/OCA/l10n-romania",
  'author': 'Dakai SOFT SRL',
  'maintainers': ["adrian-dks"],
  'license': 'OPL-1',
  'installable': True,
  'data': [
    'security/ir.model.access.csv',
    'views/stock_valuation_layer_tracking.xml',
    ],
  'category': 'Localization',
  'depends': ['l10n_ro_stock_account'],
  'maintainers': ["adrian-dks"],
}
