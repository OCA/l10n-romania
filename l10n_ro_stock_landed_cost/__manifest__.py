# Copyright (C) 2022 NextERP Romania SRL
# License OPL-1.0 or later
# (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#).

{
    "name": "Stock Landed Cost romania",
    "version": "14.0.2.0.0",
    "depends": [
        "stock_landed_costs",
        "l10n_ro_stock_account",
        # to function only if company_id.l10n_ro_accounting
        # to have only stock_account in product category
    ],
    "summary": "Stock Landed Cost for romania accounting ",
    "data": [],
    "author": "Odoo Community Association (OCA), NextERP Romania",
    "website": "https://github.com/OCA/l10n-romania",
    "support": "contact@nexterp.ro",
    "installable": True,
    "auto_install": False,
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
    "license": "AGPL-3",
}
