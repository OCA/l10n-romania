# ©  2015-2021 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details
{
    "name": "Romania - Point of Sale",
    "version": "19.0.1.9.0",
    "category": "Localization",
    "countries": ["ro"],
    "license": "AGPL-3",
    "author": "Terrabit,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": ["point_of_sale", "l10n_ro_config"],
    "maintainers": ["dhongu", "cristianPanaite"],
    "data": [
        "views/report_saledetails.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "l10n_ro_pos/static/src/**/*",
        ],
    },
}
