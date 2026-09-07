# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_ro_retail_price_change_count = fields.Integer(
        compute="_compute_l10n_ro_retail_price_change_count",
        string="Retail Price Changes",
    )

    def _l10n_ro_retail_price_change_domain(self):
        self.ensure_one()
        return [
            ("product_id", "in", self.product_variant_ids.ids),
            ("document_id.state", "=", "done"),
        ]

    @api.depends("product_variant_ids")
    def _compute_l10n_ro_retail_price_change_count(self):
        Line = self.env["l10n.ro.retail.price.change.line"]
        for template in self:
            template.l10n_ro_retail_price_change_count = Line.search_count(
                template._l10n_ro_retail_price_change_domain()
            )

    def action_l10n_ro_retail_price_history(self):
        """Every shelf price this product has had, and the document that
        decided each of them."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Retail Price History"),
            "res_model": "l10n.ro.retail.price.change.line",
            "view_mode": "list",
            "views": [
                (
                    self.env.ref(
                        "l10n_ro_stock_account_retail_price_change."
                        "view_retail_price_change_line_history_list"
                    ).id,
                    "list",
                )
            ],
            "domain": self._l10n_ro_retail_price_change_domain(),
            "context": {"create": False, "edit": False},
        }
