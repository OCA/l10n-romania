# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Romania - Localization Config",
    "summary": "Romania - Localization Install and Config Applications",
    "license": "AGPL-3",
    "countries": ["ro"],
    "version": "19.0.0.5.0",
    "author": "NextERP Romania,"
    "Forest and Biomass Romania,"
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": ["l10n_ro"],
    "data": [
        "security/ro_menus_group.xml",
        "views/account_journal.xml",
        "views/common_report.xml",
        "views/res_bank_view.xml",
        "views/res_partner_view.xml",
        "wizard/res_config_settings_views.xml",
    ],
    "pre_init_hook": "pre_init_hook",
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
    "installable": True,
    "auto_install": True,
}
