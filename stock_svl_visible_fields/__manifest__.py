# Copyright (C) 2022 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#).

{
    "name": "Stock Valuation svl detailed visible fields ",
    "version": "14.0.1.3.0",
    "depends": ["l10n_ro_stock_account"],
    "summary": "Stock Valuation Layer slv form and tree view with visible and clearer field",
    "data": [
        "views/stock_valuation_layer_views.xml",
        "views/stock_move_views.xml",
        "views/account_move_views.xml",
        "views/stock_picking_views.xml",
    ],
    "author": "NextERP Romania",
    "website": "https://github.com/OCA/l10n-romania",
    "support": "contact@nexterp.ro",
    "installable": True,
    "auto_install": False,
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
    "license": "AGPL-3",
}
