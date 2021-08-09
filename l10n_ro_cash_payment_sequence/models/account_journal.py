from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    cash_in_sequence_id = fields.Many2one(
        "ir.sequence", string="Sequence cash in", copy=False
    )
