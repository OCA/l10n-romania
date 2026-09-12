# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Retail Landed Cost (Marfa in Magazin)",
    "version": "19.0.1.0.0",
    "category": "Localization",
    "countries": ["ro"],
    "summary": "Romania - Keep 371 at the shelf price when a landed cost "
    "raises the cost of goods held in a shop",
    "author": "NextERP Romania,Dakai Soft SRL,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": [
        "l10n_ro_stock_account_retail",
        "l10n_ro_stock_account_landed_cost",
    ],
    "license": "AGPL-3",
    "data": [
        "views/stock_landed_cost_view.xml",
    ],
    "installable": True,
    # A bridge that keeps 371 at the shelf price. Without it any landed cost
    # or price difference on goods held in a shop raises 371 above the price
    # on the label, silently, so it belongs wherever both its dependencies
    # are - like the other bridges of this family. The price difference
    # bridge, which depends on this one and is itself auto installed, could
    # never install on its own while this one waited to be asked for.
    "auto_install": True,
    "development_status": "Mature",
    "maintainers": ["feketemihai", "adrian-dks"],
}
