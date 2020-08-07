# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Romania - Account Balance Sheet Report",
    "category": "Localization",
    "summary": "Romania - Balance Sheet Report",
    "depends": ["account", "l10n_ro"],
    "data": ["views/l10n_ro_anaf_reports.xml", "security/ir.model.access.csv",],
    "license": "AGPL-3",
    "version": "13.0.1.0.0",
    "author": "NextERP Romania, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "external_dependencies": {"python": ["pdfminer.six"]},
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
}
