# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Romania - Localization Config",
    "summary": "Romania - Localization Install and Config Applications",
    "license": "AGPL-3",
    "version": "15.0.1.1.0",
    "author": "NextERP Romania,"
    "Forest and Biomass Romania,"
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": ["l10n_ro", "base_vat"],
    "data": [
        "views/res_partner_view.xml",
        "views/common_report.xml",
        "views/res_config_view.xml",
        "views/res_bank_view.xml",
    ],
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
    "installable": True,
    "auto_install": True,
}
