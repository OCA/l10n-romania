# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_last_in(self, date=None):
        """The price unit of the last incoming move is used as the cost of the
        product (empty FIFO stock, valuation at date). It must be the unit
        value of the move, not the price of a kit it was sold in, see
        ``stock.move._get_kit_value_per_unit``."""
        return (
            super()._get_last_in(date=date).with_context(l10n_ro_no_kit_price_unit=True)
        )
