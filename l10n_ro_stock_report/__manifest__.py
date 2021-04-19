# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Romania - Stock Report",
    "license": "AGPL-3",
    "version": "13.0.1.0.0",
    "author": "Terrabit,NextERP Romania,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "category": "Warehouse",
    "depends": [
        "l10n_ro_stock_account",
        "date_range",
        # "web_list_view_general_buttons"
    ],
    "data": [
        "report/stock_report_view.xml",
        "report/stock_report_template.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "maintainers": ["dhongu", "feketemihai"],
}
