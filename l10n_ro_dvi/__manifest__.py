# ©  2008-2020 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details
{
    "name": "Romania - DVI",
    "license": "AGPL-3",
    "version": "13.0.1.0.0",
    "author": "Terrabit," "Odoo Community Association (OCA)",
    "website": "http://www.terrabit.ro",
    "category": "Warehouse",
    "depends": [
        "stock_account",
        "account",
        "sale",
        "l10n_ro",  # pentru determinare de conturi 446. 447
        "purchase_stock",
        "stock_landed_costs",
    ],
    "data": [
        "views/account_invoice_view.xml",
        "views/stock_landed_cost_view.xml",
        "wizard/account_dvi_view.xml",
    ],
    "installable": True,
}
