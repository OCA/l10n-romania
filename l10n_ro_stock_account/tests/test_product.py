# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import Form

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


class TestStockSale(TestStockCommon):
    def test_product_category(self):

        category = Form(self.category.copy())
        category.property_stock_valuation_account_id = self.account_valuation_mp

        category = category.save()

        self.assertEqual(
            category.property_stock_account_output_categ_id, self.account_valuation_mp
        )
        self.assertEqual(
            category.property_stock_account_input_categ_id, self.account_valuation_mp
        )
