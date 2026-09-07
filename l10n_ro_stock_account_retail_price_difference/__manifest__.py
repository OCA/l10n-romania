# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Retail Price Difference (Marfa in Magazin)",
    "version": "19.0.1.0.0",
    "category": "Localization",
    "countries": ["ro"],
    "summary": "Romania - Show what a vendor bill price difference does to "
    "the markup of goods held in a shop, before posting it",
    "author": "NextERP Romania,Dakai Soft SRL,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": [
        "l10n_ro_stock_account_retail_landed_cost",
        "l10n_ro_stock_price_difference",
    ],
    "license": "AGPL-3",
    "data": [
        "wizard/price_difference_confirmation.xml",
    ],
    "installable": True,
    "auto_install": True,
    "development_status": "Mature",
    "maintainers": ["feketemihai", "adrian-dks"],
}
