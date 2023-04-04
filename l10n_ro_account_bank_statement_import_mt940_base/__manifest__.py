# Copyright (C) 2013-2015 Therp BV <http://therp.nl>
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Romania - MT940 Bank Statements Import",
    "summary": "Romania - MT940 Bank Statements Import",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "author": "NextERP Romania," "Odoo Community Association (OCA)," "Therp BV",
    "website": "https://github.com/OCA/l10n-romania",
    "category": "Localization",
    "depends": ["account_statement_import", "l10n_ro_config"],
    "data": ["views/res_bank_view.xml"],
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["feketemihai", "dhongu"],
}
