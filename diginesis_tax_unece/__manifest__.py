{
    "name": "Diginesis Account Tax UNECE",
    "version": "12.0",
    "category": "Generic Modules/Company",
    "license": "AGPL-3",
    "summary": "UNECE nomenclature for taxes",
    "author": "SC Diginesis SRL",
    "website": "http://www.diginesis.com",
    "depends": ["account", "diginesis_base_unece"],
    "data": [
        "views/account_tax.xml",
        "views/account_tax_template.xml",
        "views/res_partner_view.xml",
        "data/unece_tax_type.xml",
        "data/unece_tax_categ.xml",
        "data/unece_tax_scheme.xml",
    ],
    "installable": True,
}
