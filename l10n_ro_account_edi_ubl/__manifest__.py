# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - eFactura Account EDI UBL",
    "category": "Localization",
    "summary": "Romania - eFactura - Account EDI UBL",
    "depends": [
        "l10n_ro_efactura",
        "l10n_ro_partner_create_by_vat",
    ],
    "data": [
        "data/account_edi_data.xml",
        "views/res_config_settings_views.xml",
        "views/account_invoice.xml",
        "views/cius_template.xml",
    ],
    "license": "AGPL-3",
    "version": "17.0.1.0.1",
    "author": "Terrabit," "NextERP Romania," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["dhongu", "feketemihai"],
}
