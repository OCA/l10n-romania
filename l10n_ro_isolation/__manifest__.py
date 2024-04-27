# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Romania - isolation",
    "summary": "Romania - isolation ",
    "license": "AGPL-3",
    "version": "16.0.1.0.0",
    "author": "NextERP Romania,"
    "Forest and Biomass Romania,"
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": ["l10n_ro", "base_vat"],
    "data": [
        "security/ro_menus_group.xml",
        "views/res_config_view.xml",
    ],
    "development_status": "Mature",
    "maintainers": ["dhongu", "feketemihai"],
    "installable": True,
    "auto_install": True,
}
