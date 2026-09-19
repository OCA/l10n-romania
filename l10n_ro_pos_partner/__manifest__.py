# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Point of Sale Partner",
    "summary": "Search a customer by CUI in the Point of Sale and create it from ANAF",
    "version": "19.0.1.1.0",
    "category": "Localization",
    "countries": ["ro"],
    "license": "AGPL-3",
    "author": "NextERP Romania,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": [
        "l10n_ro_pos",
        "l10n_ro_partner_create_by_vat",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "l10n_ro_pos_partner/static/src/**/*",
        ],
    },
    "installable": True,
    "development_status": "Alpha",
    "maintainers": ["feketemihai"],
}
