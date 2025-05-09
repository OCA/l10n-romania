# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile la achizitie

import logging

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import (
    TestStockCommon as TestStockCommonBase,
)

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockCommon(TestStockCommonBase):
    def create_lc(self, picking, lc_p1, lc_p2, vendor_bill=False):
        default_vals = self.env["stock.landed.cost"].default_get(
            list(self.env["stock.landed.cost"].fields_get())
        )
        default_vals.update(
            {
                "picking_ids": [picking.id],
                "account_journal_id": self.company_data["default_journal_misc"],
                "cost_lines": [(0, 0, {"product_id": self.product_1.id})],
                "valuation_adjustment_lines": [],
                "vendor_bill_id": vendor_bill and vendor_bill.id or False,
            }
        )
        cost_lines_values = {
            "name": ["equal split"],
            "split_method": ["equal"],
            "price_unit": [lc_p1 + lc_p2],
        }
        stock_landed_cost_1 = self.env["stock.landed.cost"].new(default_vals)
        for index, cost_line in enumerate(stock_landed_cost_1.cost_lines):
            cost_line.onchange_product_id()
            cost_line.name = cost_lines_values["name"][index]
            cost_line.split_method = cost_lines_values["split_method"][index]
            cost_line.price_unit = cost_lines_values["price_unit"][index]
        vals = stock_landed_cost_1._convert_to_write(stock_landed_cost_1._cache)
        stock_landed_cost_1 = self.env["stock.landed.cost"].create(vals)

        stock_landed_cost_1.compute_landed_cost()
        stock_landed_cost_1.button_validate()
        return stock_landed_cost_1
