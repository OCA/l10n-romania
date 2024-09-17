# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Stock Accounting Price Difference",
    "version": "17.0.0.3.0",
    "category": "Localization",
    "summary": "Romania - Stock Accounting Price Difference",
    "author": "NextERP Romania," "Dorin Hongu," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": [
        "l10n_ro_stock_account_landed_cost",
        "l10n_ro_stock_account_notice",
        "stock_landed_costs",
        "purchase_stock",
    ],
    "license": "AGPL-3",
    "data": [
        "wizard/price_difference_confirmation.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "auto_install": False,
    "development_status": "Mature",
    "maintainers": ["feketemihai", "mcojocaru", "dhongu"],
}
