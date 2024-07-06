# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ro_message_spv_ids = fields.One2many(
        "l10n.ro.message.spv",
        "invoice_id",
        string="Romania - E-invoice messages",
        help="E-invoice messages related to this invoice.",
    )
