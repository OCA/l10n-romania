# Copyright 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # TO-DO Add migration script
    l10n_ro_print_report = fields.Boolean(
        related="bank_account_id.l10n_ro_print_report", store=True
    )
