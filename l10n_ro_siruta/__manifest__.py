# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Romania - Siruta",
    "category": "Localization",
    "summary": "Romania - Siruta",
    "depends": ["contacts", "l10n_ro_city"],
    "data": [
        "data/res_country_zone.xml",
        "data/res_country_state.xml",
        "data/res_country_commune.xml",
        "views/partner_view.xml",
        "views/l10n_ro_res_country_commune_views.xml",
        "views/l10n_ro_res_country_zone_views.xml",
        "views/res_city_views.xml",
        "views/res_country_state_views.xml",
        "security/ir.model.access.csv",
    ],
    "demo": ["demo/demo_siruta.xml"],
    "qweb": [
        "static/src/xml/assets.xml",
    ],
    "license": "AGPL-3",
    "version": "15.0.2.5.0",
    "author": "NextERP Romania,"
    "Forest and Biomass Romania,"
    "Terrabit,"
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "installable": True,
    "development_status": "Mature",
    "post_init_hook": "post_init_hook",
    "maintainers": ["feketemihai", "dhongu"],
}
