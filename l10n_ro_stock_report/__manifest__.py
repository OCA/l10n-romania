# ©  2008-2020 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details
{
    "name": "Romania - Stock Report",
    "license": "AGPL-3",
    "version": "13.0.1.0.0",
    "author": "Terrabit,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "category": "Warehouse",
    "depends": [
        "stock_account",
        "account",
        "purchase_stock",
        "sale_stock",
        "date_range",
    ],
    "data": [
        "report/daily_stock_report_view.xml",
        "report/daily_stock_report_template.xml",
        "report/storage_sheet_report_view.xml",
        "report/storage_sheet_report_template.xml",
        "report/stock_report_view.xml",
    ],
}
