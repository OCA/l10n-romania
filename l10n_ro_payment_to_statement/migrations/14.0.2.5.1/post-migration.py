# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    # Create cash journals sequences if not set already
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        ro_comps = env["res.company"].search([("l10n_ro_accounting", "=", True)])
        if ro_comps:
            cash_journals = env["account.journal"].search(
                [("type", "=", "cash"), ("company_id", "in", ro_comps.ids)]
            )
            for journal in cash_journals:
                new_vals = {
                    "name": journal.name,
                    "code": journal.code,
                    "company_id": journal.company_id.id,
                    "l10n_ro_auto_statement": True,
                    "l10n_ro_statement_sequence_id": journal.l10n_ro_statement_sequence_id.id,
                    "l10n_ro_cash_in_sequence_id": journal.l10n_ro_cash_in_sequence_id.id,
                    "l10n_ro_cash_out_sequence_id": journal.l10n_ro_cash_out_sequence_id.id,
                    "l10n_ro_customer_cash_in_sequence_id": journal.l10n_ro_customer_cash_in_sequence_id.id,
                }
                journal._fill_missing_values(new_vals)
                journal.write(new_vals)
