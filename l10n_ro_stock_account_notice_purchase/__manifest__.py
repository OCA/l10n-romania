# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Stock Accounting Notice with Purchase",
    "version": "14.0.1.0.0",
    "category": "Localization",
    "summary": """Romania - Stock Accounting Notice with purchase installed.
    With this module at reception (picking) with notice for romainan company will
    at pressing the create bill from puchase will set the l10n_ro_bill_for_pickings_ids with all the notice picking reception
    
     Is beeng automaticaly installed if is l10n_ro_stock_account_notice & purchase_stock are installed.
""",
    "author": "cbssolutions.ro, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": [
        "purchase_stock",
        "l10n_ro_stock_account_notice",
    ],
    "license": "AGPL-3",
    "data": [],
    "installable": True,
    "auto_install": True,
    "maintainers": ["dev@cbssolutions.ro"],
}
