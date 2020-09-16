# ©  2008-2020 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

{
    "name": "Romanian  Intrastat Declaration",
    "license": "AGPL-3",
    "version": "13.0.1.0.0",
    "author": "Dorin Hongu," "Odoo Community Association (OCA)",
    "depends": ["product", "sale_stock", "account", "l10n_ro"],
    "data": [
        "data/country_data.xml",
        "data/transaction.codes.xml",
        "data/transport.modes.xml",
        "security/groups.xml",
        "security/ir.model.access.csv",
        "views/l10n_ro_intrastat_view.xml",
        "views/account_move_view.xml",
        "views/product_view.xml",
        "views/res_country_view.xml",
        "views/account_intrastat_code_view.xml",
        "wizard/l10n_ro_intrastat_xml_view.xml",
        "views/res_config_settings.xml",
    ],
    "development_status": "beta",
    "maintainers": ["dhongu"],
}
