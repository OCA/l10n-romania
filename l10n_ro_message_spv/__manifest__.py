# Copyright (C) 2024 Dorin Hongu <dhongu(@)gmail(.)com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Romania - Mesaje SPV",
    "category": "Localization",
    "summary": "Romania - Mesaje SPV",
    "depends": ["l10n_ro_account_anaf_sync", "l10n_ro_account_edi_ubl"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "data/ir_cron_data.xml",
        "views/message_spv_view.xml",
        "views/assets.xml",
    ],
    "qweb": [
        "static/src/xml/message_spv.xml",
    ],
    "license": "AGPL-3",
    "version": "14.0.1.1.0",
    "author": "Terrabit," "NextERP Romania," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "installable": True,
    "development_status": "Beta",
    "maintainers": ["dhongu"],
}
