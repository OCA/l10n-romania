# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockValuationLayerRevaluation(models.TransientModel):
    _name = "stock.valuation.layer.revaluation"
    _inherit = ["stock.valuation.layer.revaluation", "l10n.ro.mixin"]

    l10n_ro_location_id = fields.Many2one(
        "stock.location",
    )

    @api.onchange("l10n_ro_location_id")
    def onchange_location_id(self):
        if self.l10n_ro_location_id:
            self.current_value_svl = self.product_id.with_context(
                location_id=self.l10n_ro_location_id.id
            ).value_svl
            self.current_quantity_svl = self.product_id.with_context(
                location_id=self.l10n_ro_location_id.id
            ).quantity_svl

    def action_validate_revaluation(self):
        self.ensure_one()
        if self.is_l10n_ro_record and self.l10n_ro_location_id:
            self.product_id = self.product_id.with_context(
                location_id=self.l10n_ro_location_id.id
            )
        return super().action_validate_revaluation()
