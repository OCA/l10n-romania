# ©  2008-2022 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details
{
    "name": "Romania - EDI UBL",
    "license": "AGPL-3",
    "version": "14.0.0.0.3",
    "author": "Terrabit," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "category": "Tools",
    "depends": [
        "l10n_ro_config",
        "account_edi_ubl",
        "account_edi_ubl_bis3",
    ],
    "data": [
        "data/account_edi_data.xml",
        "data/ubl_templates.xml",
        "views/res_config_settings_views.xml",
        "views/account_invoice.xml",
    ],
    "installable": True,
}
