# ©  2015-2021 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details
{
    "name": "Romania - Point of Sale",
    "version": "14.0.2.3.0",
    "category": "Localization",
    "license": "AGPL-3",
    "author": "Terrabit,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": ["point_of_sale", "l10n_ro_stock", "l10n_ro_config"],
    "data": [
        "views/assets.xml",
        "views/report_saledetails.xml",
    ],
    "qweb": ["static/src/xml/pos.xml"],
    "maintainers": ["dhongu"],
}
