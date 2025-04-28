# Copyright (C) 2025 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import Command
from odoo.fields import Date
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ro_stock_account.tests.common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockLandedCost(TestStockCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("ro")
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass()

    def test_create_lc(self):
        self.categ_real_time = self.env.ref("product.product_category_all").copy(
            {
                "property_valuation": "real_time",
                "property_cost_method": "fifo",
                "property_stock_account_input_categ_id": self.account_valuation.id,
                "property_stock_account_output_categ_id": self.account_valuation.id,
                "property_stock_valuation_account_id": self.account_valuation.id,
            }
        )
        product = self.env["product.product"].create(
            {
                "name": "product",
                "is_storable": True,
                "standard_price": 10,
                "categ_id": self.categ_real_time.id,
            }
        )
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": 1,
                        }
                    )
                    for _ in range(6)
                ],
            }
        )
        po.button_confirm()
        po.picking_ids.button_validate()

        po.action_create_invoice()
        bill = po.invoice_ids
        bill.invoice_date = Date.today()
        with Form(bill) as bill_form:
            with bill_form.invoice_line_ids.new() as inv_line:
                inv_line.product_id = self.landed_cost
                inv_line.price_unit = 6.85
                inv_line.is_landed_costs_line = True
        bill.action_post()
        action = bill.button_create_landed_costs()
        self.assertEqual(action.get("name"), "Landed Costs")

        picking_landed = self.env["stock.landed.cost"].search(
            [("picking_ids", "in", po.picking_ids.id)]
        )
        picking_landed_cost = picking_landed.filtered(
            lambda x: x.cost_lines.product_id == self.landed_cost
        )

        accounts = self.landed_cost.product_tmpl_id._get_product_accounts()

        self.assertEqual(
            picking_landed_cost.cost_lines.account_id.id, accounts["expense"].id
        )
        self.assertEqual(picking_landed_cost.amount_total, 6.85)

        bill.landed_costs_ids.button_validate()
        svl_aj = self.env["stock.valuation.adjustment.lines"].search(
            [("product_id", "=", product.id)]
        )

        self.assertEqual(svl_aj[0].name, "Landed Cost - product")
        self.assertEqual(sum(svl_aj.mapped("additional_landed_cost")), 6.85)
