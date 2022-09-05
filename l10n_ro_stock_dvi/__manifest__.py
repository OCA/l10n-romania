# © 2022 cbssolutions.ro
# © 2022 NextERP Romania SRL
# ©  2008-2020 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details
{
    "name": "Romania - DVI",
    "license": "AGPL-3",
    "version": "14.0.4.0.0",
    "author": "NextERP Romania, Terrabit ,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "category": "Warehouse",
    "sumarry": "Declaratie Vamala de Import DVI for romania accounting",
    "depends": [
        "l10n_ro_stock_landed_cost",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_invoice_view.xml",
        "views/stock_landed_cost_view.xml",
        "views/product_template_view.xml",
        "wizard/account_dvi_view.xml",
    ],
    "installable": True,
    "post_init_hook": "_post_init_hook_create_dvi_products",
}
