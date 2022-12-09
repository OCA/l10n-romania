from . import models

from odoo import SUPERUSER_ID, api


def pre_init_hook(cr, registry):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        ro_comps = env["res.company"].search([("l10n_ro_accounting", "=", True)])
        if ro_comps:
            cash_journals = env["account.journal"].search(
                [("type", "=", "cash"), ("company_id", "in", ro_comps.ids)]
            )
            for journal in cash_journals:
                journal.l10n_ro_update_cash_vals()
