# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Account EDI UBL",
    "category": "Localization",
    "summary": "Romania - Account EDI UBL",
    "depends": [
        "l10n_ro_account_anaf_sync",
        "account_edi_ubl_cii",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/account_edi_data.xml",
        "data/ubl_templates.xml",
        "views/res_config_settings_views.xml",
        "views/account_invoice.xml",
        "views/product_view.xml",
        "views/res_partner_view.xml",
        "views/cius_template.xml",
    ],
    "license": "AGPL-3",
    "version": "14.0.1.8.0",
    "author": "Terrabit," "NextERP Romania," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "installable": True,
    "development_status": "Mature",
    "pre_init_hook": "pre_init_hook",
    "maintainers": ["dhongu", "feketemihai"],
}
