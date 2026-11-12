# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["product.product", "l10n.ro.mixin"]

    def _l10n_ro_filter_costing_change_layers(self, stock_valuation_layers):
        """Split the layers between the Romanian ones and the others.

        In Romanian accounting the input, output and valuation accounts of a
        category are the same, so the entries the standard builds when the
        costing or the valuation method changes are always account 371 against
        account 371 (or 301, 345, ...): a balanced entry with no meaning that
        only pollutes the stock journal. The value itself does not move from
        one account to another, only the costing method changes.
        """
        l10n_ro_layers = stock_valuation_layers.filtered(
            lambda svl: svl.company_id.l10n_ro_accounting
        )
        if l10n_ro_layers:
            _logger.debug(
                "Skipping costing change entries for layers %s", l10n_ro_layers.ids
            )
        return stock_valuation_layers - l10n_ro_layers

    def _svl_empty_stock_am(self, stock_valuation_layers):
        return super()._svl_empty_stock_am(
            self._l10n_ro_filter_costing_change_layers(stock_valuation_layers)
        )

    def _svl_replenish_stock_am(self, stock_valuation_layers):
        return super()._svl_replenish_stock_am(
            self._l10n_ro_filter_costing_change_layers(stock_valuation_layers)
        )
