# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Romania - Human Resources",
    "category": "Localization",
    "summary": "Romania  - Human Resources",
    "depends": ["hr", "hr_employee_firstname"],
    "external_dependencies": {
        "python": ["stdnum"],
    },
    "data": [
        "views/hr_employee_view.xml",
        "views/res_company_view.xml",
        "security/ir.model.access.csv",
    ],
    "demo": ["data/hr_demo.xml"],
    "license": "AGPL-3",
    "version": "11.0.1.0.0",
    "author": "NextERP Romania,"
    "Forest and Biomass Romania,"
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
}
