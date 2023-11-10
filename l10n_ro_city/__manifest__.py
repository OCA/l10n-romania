# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Romania - City",
    "summary": "Romania - City",
    "license": "AGPL-3",
    "version": "15.0.3.5.0",
    "author": "Terrabit,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "category": "Localization",
    "depends": ["base_address_city", "l10n_ro_config"],
    "data": [
        "data/res_city.xml",
        "views/res_city_view.xml",
        "data/res.country.state.csv",
    ],
    "development_status": "Mature",
    "installable": True,
    "maintainers": ["dhongu"],
}
