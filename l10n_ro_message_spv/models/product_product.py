from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _import_retrieve_product_from_vendor_code(self, product_values):
        vendor_code = product_values.get("l10n_ro_vendor_code")
        if vendor_code:
            return {
                "criteria": [
                    {"domain": [("seller_ids.product_code", "=", vendor_code)]}
                ]
            }

    def _get_retrieval_product_search_plan(self):
        # Insert vendor code search with highest priority
        # (lowest number = highest priority)
        return [
            (1, self._import_retrieve_product_from_vendor_code)
        ] + super()._get_retrieval_product_search_plan()
