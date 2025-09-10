# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Romania - City",
    "summary": "Romania - City",
    "countries": ["ro"],
    "license": "AGPL-3",
    "version": "18.0.1.6.0",
    "author": "Terrabit,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "category": "Localization",
    "depends": ["base_address_extended", "l10n_ro_config"],
    "data": [
        "data/res_city.xml",
        "views/res_city_view.xml",
        "data/res.country.state.csv",
    ],
    "development_status": "Mature",
    "installable": True,
    "maintainers": ["dhongu"],
}
