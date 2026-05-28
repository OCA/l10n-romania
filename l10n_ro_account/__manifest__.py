# ©  2020 Terrabit
# See README.rst file on addons root folder for license details


{
    "name": "Romania - Account",
    "version": "19.0.0.5.0",
    "summary": "Romania - Account",
    "countries": ["ro"],
    "license": "AGPL-3",
    "author": "Terrabit,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "category": "Localization",
    "depends": ["account", "l10n_ro", "l10n_ro_config", "account_reports"],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "l10n_ro_account/static/src/search_bar_patch.js",
        ],
    },
    "maintainers": ["dhongu"],
}
