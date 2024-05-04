# Copyright (C) 2023 Dorin Hongu <dhongu(@)gmail(.)com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - E-Trasnport",
    "category": "Localization",
    "countries": ["ro"],
    "summary": "Romania - E-Trasnport",
    "depends": [
        "l10n_ro_config",
        "l10n_ro_account_anaf_sync",
        "l10n_ro_stock",
        "stock",
        "delivery",
    ],
    "data": [
        "views/stock_picking_view.xml",
        "views/e_transport_template.xml",
        "views/delivery_view.xml",
        "views/l10n_ro_e_transport_view.xml",
        "security/ir.model.access.csv",
        "data/l10n.ro.e.transport.scope.csv",
        "data/l10n.ro.e.transport.customs.csv",
        "data/l10n.ro.e.transport.operation.csv",
    ],
    "license": "AGPL-3",
    "version": "17.0.0.3.1",
    "author": "Terrabit," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "installable": True,
    "development_status": "Beta",
    "maintainers": ["dhongu"],
}
