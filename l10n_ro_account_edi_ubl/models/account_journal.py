# Copyright 2020 NextERP Romania
# License LGPL-3
# (https://www.gnu.org/licenses/lgpl-3.0.html).

from odoo import fields, models

SEQUENCE_TYPE = [
    ("normal", "Invoice"),
    ("autoinv1", "Customer Auto Invoicing"),
    ("autoinv2", "Supplier  Auto Invoicing"),
]


class AccountJournal(models.Model):
    _name = "account.journal"
    _inherit = ["account.journal", "l10n.ro.mixin"]

    l10n_ro_partner_id = fields.Many2one("res.partner", "Ro Partner", default=None)
    l10n_ro_sequence_type = fields.Selection(
        selection=SEQUENCE_TYPE, string="Ro Sequence Type", default="normal"
    )