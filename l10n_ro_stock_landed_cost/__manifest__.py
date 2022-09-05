# Copyright (C) 2022 NextERP Romania SRL
# Copyright (C) 2022 cbssolutions.ro
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#).

{
    "name": "Stock Landed Cost romania",
    "version": "14.0.4.0.0",
    "depends": [
        "stock_landed_costs",
        "l10n_ro_stock_account",
    ],
    "summary": "Stock Landed Cost for romania accounting ",
    "data": ["views/stock_landed_cost_views.xml"],
    "author": "cbssolutions.ro, NextERP Romania, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "support": "dev@cbssolutions.ro",
    "installable": True,
    "auto_install": False,
    "development_status": "Mature",
    "maintainers": ["dev@cbssolutions.ro"],
    "license": "AGPL-3",
}
