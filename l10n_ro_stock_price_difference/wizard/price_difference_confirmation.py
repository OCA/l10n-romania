# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class PriceDifferenceConfirmation(models.TransientModel):
    _name = "l10n_ro.price_difference_confirm_dialog"
    _description = "Wizard to show price differences between invoice and reception"

    invoice_id = fields.Many2one("account.move", readonly=True)
    item_ids = fields.One2many(
        "l10n_ro.price_difference_item", "confirmation_id", readonly=True
    )

    def action_confirm(self):
        return self.invoice_id.with_context(
            l10n_ro_approved_price_difference=True
        ).action_post()


class PriceDifferenceItem(models.TransientModel):
    _name = "l10n_ro.price_difference_item"
    _description = (
        "Item from Wizard to show price differences between invoice and reception"
    )

    confirmation_id = fields.Many2one("l10n_ro.price_difference_confirm_dialog")
    invoice_id = fields.Many2one("account.move")
    picking_id = fields.Many2one("stock.picking")
    product_id = fields.Many2one("product.product")
    amount_difference = fields.Monetary()
    quantity_difference = fields.Float()
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )
