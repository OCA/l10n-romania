# Copyright (C) 2020 NextERP Romania S.R.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    compensation_line_id = fields.Many2one(
        "account.compensation.line", string="Compensation Line", readonly=True
    )
