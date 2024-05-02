# Copyright (C) 2019 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Romania - Account ANAF Sync",
    "category": "Localization",
    "countries": ["ro"],
    "summary": "Romania - Account ANAF Sync",
    "depends": ["l10n_ro_config"],
    "data": [
        "security/account_security.xml",
        "security/ir.model.access.csv",
        "views/l10n_ro_account_anaf_sync_view.xml",
        "wizard/res_config_settings_views.xml",
        "views/template.xml",
    ],
    "license": "AGPL-3",
    "version": "17.0.1.2.1",
    "author": "NextERP Romania," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
    "external_dependencies": {"python": ["PyJWT"]},
}
