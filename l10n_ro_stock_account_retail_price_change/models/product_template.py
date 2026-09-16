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

    def write(self, vals):
        """A shop priced off the sale price re-prices its shelves here.

        ``base='list_price'`` is the default of a formula rule and the most
        common way a shop is set up: the shelf price is the sale price, or the
        sale price less a discount. For that shop the repricing action is
        editing the product, and nothing at all is written on the pricelist -
        so watching only ``product.pricelist.item`` saw none of it, and 371
        stayed on the old price with no document raised.

        The cost is the other base a formula can have, and it is deliberately
        not watched here. ``standard_price`` is written by the valuation on
        every reception under average cost, which is the hot path of every
        goods movement in the database, and hanging a price snapshot off it
        would make every receipt pay for a check that almost never finds
        anything. A shelf price that follows the cost is caught by the nightly
        reconciliation instead, which is where the other prices that move
        without anyone writing them are caught too.
        """
        Item = self.env["product.pricelist.item"]
        if self.env.context.get("skip_retail_price_change") or "list_price" not in vals:
            return super().write(vals)
        targets = self.product_variant_ids._l10n_ro_retail_shelves()
        if not targets:
            return super().write(vals)
        old_snapshot = Item._l10n_ro_prices(targets)
        res = super().write(vals)
        self.env["l10n.ro.retail.price.change"]._l10n_ro_record_moves(
            old_snapshot, Item._l10n_ro_prices(targets)
        )
        return res
