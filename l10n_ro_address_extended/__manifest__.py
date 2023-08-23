# Copyright (C) 2018 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Romania - Extended Addresses",
    "category": "Localization",
    "summary": "Romania - Extended Addresses",
    "depends": ["base_address_extended", "l10n_ro_config"],
    "data": ["views/res_company_view.xml", "views/res_partner_view.xml"],
    "pre_init_hook": "pre_init_hook",
    "license": "AGPL-3",
    "version": "15.0.2.3.0",
    "author": "NextERP Romania,"
    "Forest and Biomass Romania,"
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-romania",
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["feketemihai"],
}
