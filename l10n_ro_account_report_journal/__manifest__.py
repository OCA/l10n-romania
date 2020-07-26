# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Romania - Account Report Journal",
    "category": "Localization",
    "summary": "Romania - Account Sale and Purchase Journal Report",
    "depends": ["l10n_ro", "date_range", "l10n_ro_vat_on_payment"],
    "data": [
        "report/report_sale_purchase.xml",
        "wizard/select_report_sale_purchase_view.xml",
        "security/ir.model.access.csv",
    ],
    "license": "AGPL-3",
    "version": "13.0.1.0.0",
    "author": "NextERP Romania, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
}
