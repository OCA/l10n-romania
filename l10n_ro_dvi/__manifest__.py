# ©  2008-2020 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details
{
    "name": "Romania - DVI",
    "license": "AGPL-3",
    "version": "17.0.1.1.0",
    "author": "Terrabit," "NextERP Romania," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "category": "Localization",
    "depends": [
        "l10n_ro_stock_account_landed_cost",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_invoice_view.xml",
        "views/stock_landed_cost_view.xml",
        "views/account_dvi_view.xml",
    ],
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["dhongu", "feketemihai"],
}
