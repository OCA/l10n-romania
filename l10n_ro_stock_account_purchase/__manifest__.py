# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Stock Accounting with Purchase",
    "version": "14.0.1.0.0",
    "category": "Localization",
    "summary": """Romania - Stock Accounting with purchase installed.
    With this module at reception (picking) without notice for romainan company will
    create the bill ( like create bill from purchase ) and set it for the made recpetion
    
     Is beeng automaticaly installed if is l10n_ro_stock_account & purchase_stock are installed.
    """,
    "author": "cbssolutions.ro, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "depends": [
        "purchase_stock",
        "l10n_ro_stock_account",
    ],
    "license": "AGPL-3",
    "data": [],
    "installable": True,
    "auto_install": True,
    "maintainers": ["dev@cbssolutions.ro"],
}
