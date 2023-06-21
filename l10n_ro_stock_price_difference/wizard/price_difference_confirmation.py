# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class PriceDifferenceConfirmation(models.TransientModel):
    _name = "l10n_ro.price_difference_confirm_dialog"
    _description = "Wizard to show price differences between invoice and reception"

    invoice_id = fields.Many2one("account.move")
    message = fields.Html(default="")

    def action_confirm(self):
        return self.invoice_id.with_context(
            l10n_ro_approved_price_difference=True
        ).action_post()
