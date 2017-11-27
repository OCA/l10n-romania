# Copyright (C) 2017 FOREST AND BIOMASS ROMANIA SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


{
    "name": "Romania - Human Resources",
    "version": "11.0.1.0.0",
    "author": "FOREST AND BIOMASS ROMANIA",
    "website": "http://www.forbiom.eu",
    "category": "Localization",
    "depends": ['hr', 'hr_employee_firstname'],
    "external_dependencies": {
        'python' : ['stdnum'],
    },
    "description": "Romania  - Human Resources",
    "data": [
        "data/res.company.caen.csv",
        "views/hr_employee_view.xml",
        "views/res_company_view.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True
}
