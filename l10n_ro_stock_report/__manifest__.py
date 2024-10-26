# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Stock Report (Fișă Magazie)",
    "license": "AGPL-3",
    "version": "17.0.1.3.0",
    "countries": ["ro"],
    "author": "Terrabit,NextERP Romania,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "category": "Warehouse",
    "depends": [
        "l10n_ro_stock_account",
    ],
    "data": [
        "report/stock_report_view.xml",
        "report/stock_report_template.xml",
        "security/ir.model.access.csv",
    ],
    "qweb": ["static/src/xml/stock_sheet.xml"],
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["dhongu", "feketemihai"],
}
