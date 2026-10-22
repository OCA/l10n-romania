# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


def _l10n_ro_retail_price_history_action(env, domain):
    """The window both the template and the variant open on the history."""
    return {
        "type": "ir.actions.act_window",
        "name": env._("Retail Price History"),
        "res_model": "l10n.ro.retail.price.change.line",
        "view_mode": "list",
        "views": [
            (
                env.ref(
                    "l10n_ro_stock_account_retail_price_change."
                    "view_retail_price_change_line_history_list"
                ).id,
                "list",
            )
        ],
        "domain": domain,
        "context": {"create": False, "edit": False},
    }


class ProductProduct(models.Model):
    _inherit = "product.product"

    # The variant carries the count and the button of its own, because the
    # form of a variant is Odoo's own template form seen on
    # ``product.product`` (``product.product_normal_form_view`` inherits
    # ``product.product_template_form_view`` as a primary view). Whatever the
    # template form is given has to exist on the variant too, or every view
    # built on it -- the eCommerce one among them -- fails to validate:
    # "action_l10n_ro_retail_price_history is not a valid action on
    # product.product". It is the more useful button anyway: the history of
    # this article, not of all its variants together.
    l10n_ro_retail_price_change_count = fields.Integer(
        compute="_compute_l10n_ro_retail_price_change_count",
        string="Retail Price Changes",
    )

    def _l10n_ro_retail_price_change_domain(self):
        self.ensure_one()
        return [
            ("product_id", "=", self.id),
            ("document_id.state", "=", "done"),
        ]

    @api.depends("product_tmpl_id")
    def _compute_l10n_ro_retail_price_change_count(self):
        Line = self.env["l10n.ro.retail.price.change.line"]
        for product in self:
            product.l10n_ro_retail_price_change_count = Line.search_count(
                product._l10n_ro_retail_price_change_domain()
            )

    def action_l10n_ro_retail_price_history(self):
        """Every shelf price this variant has had, and the document that
        decided each of them."""
        self.ensure_one()
        return _l10n_ro_retail_price_history_action(
            self.env, self._l10n_ro_retail_price_change_domain()
        )

    def _l10n_ro_retail_shelves(self):
        """``{warehouse: products}`` - the retail shops holding these goods.

        The mirror of the pricelist side: there the question is which shelves
        a rule can reach, here it is which shelves hold a given article. Both
        are bounded by the quants of the retail locations, because a document
        has nothing to say about goods that are not on a shelf.
        """
        if not self:
            return {}
        groups = (
            self.env["stock.quant"]
            .sudo()
            ._read_group(
                [
                    ("product_id", "in", self.ids),
                    ("location_id.l10n_ro_retail", "=", True),
                    ("quantity", ">", 0),
                ],
                groupby=["location_id", "product_id"],
            )
        )
        empty = self.browse()
        targets = {}
        for location, product in groups:
            warehouse = location.warehouse_id
            if not warehouse.l10n_ro_retail_pricelist_id:
                continue
            targets[warehouse] = targets.get(warehouse, empty) | product
        return targets
