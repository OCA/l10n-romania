# Copyright 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models

SEQUENCE_TYPE = [
    ("normal", "Invoice"),
    ("autoinv1", "Customer Auto Invoicing"),
    ("autoinv2", "Supplier  Auto Invoicing"),
]


class AccountJournal(models.Model):
    _name = "account.journal"
    _inherit = ["account.journal", "l10n.ro.mixin"]

    # TO-DO Add migration script
    l10n_ro_print_report = fields.Boolean(
        "Ro Print in Report",
        compute="_compute_l10n_ro_print_report",
        inverse="_inverse_l10n_ro_print_report",
        store=True,
    )
    l10n_ro_fiscal_receipt = fields.Boolean("Fiscal Receipts Journal")
    l10n_ro_partner_id = fields.Many2one(
        "res.partner", "Romania - Autoinvoice Partner", default=None
    )
    l10n_ro_sequence_type = fields.Selection(
        selection=SEQUENCE_TYPE,
        string="Romania - Autoinvoice Sequence Type",
        default="normal",
    )

    @api.depends("bank_account_id.l10n_ro_print_report")
    def _compute_l10n_ro_print_report(self):
        for jr in self:
            jr.l10n_ro_print_report = jr.bank_account_id.l10n_ro_print_report

    def _inverse_l10n_ro_print_report(self):
        for jr in self:
            jr.bank_account_id.l10n_ro_print_report = jr.l10n_ro_print_report
