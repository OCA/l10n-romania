# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Nondeductible VAT",
    "category": "Localization",
    "summary": "Romania - Nondeductible VAT",
    "license": "AGPL-3",
    "version": "19.0.0.1.0",
    "data": [
        "views/account_account_view.xml",
        "views/account_move_view.xml",
        "views/account_tax_view.xml",
        "views/stock_quant_view.xml",
        "views/stock_picking_view.xml",
    ],
    "depends": ["l10n_ro_stock_account", "l10n_ro_vat_on_payment"],
    "author": "Dakai Soft SRL,NextERP Romania,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["adrian-dks", "feketemihai"],
}
