# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Romania - VAT on Payment",
    "category": "Localization",
    "summary": "Romania - VAT on Payment",
    "data": [
        "views/res_partner_view.xml",
        "security/ir.model.access.csv",
        "data/res_partner_anaf_cron.xml",
    ],
    "depends": ["l10n_ro_config"],
    "license": "AGPL-3",
    "version": "17.0.1.2.0",
    "author": "NextERP Romania,"
    "Forest and Biomass Romania,"
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "installable": True,
    "pre_init_hook": "pre_init_hook",
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
    "sequence": "99",
}
