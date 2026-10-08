# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Point of Sale Refunds",
    "summary": "Credit note and payment disposal for Point of Sale refunds",
    "version": "19.0.1.4.0",
    "category": "Localization",
    "countries": ["ro"],
    "license": "AGPL-3",
    "author": "NextERP Romania,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": [
        "l10n_ro_pos",
        "l10n_ro_payment_receipt_report",
    ],
    "data": [
        "views/pos_order_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "l10n_ro_pos_refund/static/src/**/*",
        ],
    },
    "installable": True,
    "development_status": "Alpha",
    "maintainers": ["feketemihai"],
}
