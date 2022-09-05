# Copyright (C) 2022 NextERP Romania
# Copyright (C) 2022 cbssolutions.ro
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Stock Accounting Notice",
    "version": "14.0.4.0.0",
    "category": "Localization",
    "summary": "Romania - Stock Accounting Notice",
    "author": "cbssolutions.ro, NextERP Romania, Dorin Hongu, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": ["l10n_ro_stock_account"],
    "license": "AGPL-3",
    "data": [
        "views/stock_picking_view.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "auto_install": False,  # not all companies are using notce (cumpara pe aviz)
    "maintainers": ["dev@cbssolutions.ro", "feketemihai", "dhongu"],
}
