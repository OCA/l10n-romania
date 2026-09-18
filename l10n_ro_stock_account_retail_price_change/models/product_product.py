# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

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
