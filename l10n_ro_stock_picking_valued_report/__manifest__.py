# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Stock Picking Comment Template",
    "category": "Localization",
    "summary": """
        This model is going to add a a header and a footer at picking report
         depeding on the operation type.
    """,
    "depends": [
        "sale_stock",
        "purchase_stock",
        "l10n_ro_stock_account",
        "base_comment_template",
    ],
    "data": [
        "data/l10n_ro_stock_picking_comment_template.xml",
        "views/stock_picking_view.xml",
        "views/base_comment_template_view.xml",
        "report/stock_picking_report_valued.xml",
        "report/report_picking.xml",
    ],
    "license": "AGPL-3",
    "version": "14.0.1.0.0",
    "author": "NextERP Romania," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
}
