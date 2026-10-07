# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Point of Sale for Retail Shops (Marfa in Magazin)",
    "version": "19.0.1.0.0",
    "category": "Localization",
    "countries": ["ro"],
    "summary": "Romania - A till sells on the fiscal position and the shelf "
    "prices of the shop it is attached to",
    "author": "NextERP Romania,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": [
        "l10n_ro_pos",
        "l10n_ro_stock_account_retail",
    ],
    "license": "AGPL-3",
    "demo": [
        "demo/pos_retail_demo.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    # Without it, a till attached to a shop kept at retail sells with the
    # ordinary taxes of the product and on the ordinary accounts, which is
    # not what the shop's own books say. Whoever has both halves installed
    # wants them to agree, so the bridge belongs there by itself.
    "auto_install": True,
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
}
