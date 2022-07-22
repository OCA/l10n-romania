{
    "name" : "Diginesis Invoice UBL",
    "version" : "12.0",
    "author" : "SC Diginesis SRL",
    "website" : "http://www.diginesis.com",
    "category" : "Generic Modules/Company",
    "summary": "Generate UBL XML file for customer invoices/refunds", 
    "description": """
This modules includes
	- "Institution of State" option on partner
	- "Institution of State" option on invoice
""",
    "depends" : ["base", "account", "diginesis_base_ubl", "diginesis_base_ubl_payment", "sale", "diginesis_tax_unece"],
    "init_xml" : [],
    "data" : ["security/ir.model.access.csv",
			 "views/report.xml", 
			 "data/data.xml",
			 "views/res_partner_view.xml",
			 "views/account_invoice_view.xml",
			 
			 ],
    "demo_xml" : [],
    "active": False,
    'installable': True,
    'auto_install': False,
}