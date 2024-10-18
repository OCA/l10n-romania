# Copyright (C) 2024 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import Form, tagged

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


# Generare note contabile la achizitie


@tagged("post_install", "-at_install")
class TestStockDropshiping(TestStockCommon):
    def test_dropshiping(self):
        # creare comanda de vanzre cu dropshiping
        _logger.debug("Start sale")

        so_form = Form(self.env["sale.order"])
        so_form.partner_id = self.client
        dropshipping_route = self.env.ref("stock_dropshipping.route_drop_shipping")
        self.product_1.write(
            {
                "route_ids": [(4, dropshipping_route.id, 0)],
                "seller_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": self.vendor.id,
                        },
                    )
                ],
            }
        )

        with so_form.order_line.new() as so_line:
            so_line.product_id = self.product_1
            so_line.product_uom_qty = self.qty_so_p1

        sale_order = so_form.save()

        # Confirm sales order
        sale_order.action_confirm()

        purchase = self.env["purchase.order"].search(
            [("partner_id", "=", self.vendor.id)]
        )
        purchase.button_confirm()

        for move_line in sale_order.picking_ids.move_ids:
            if move_line.product_uom_qty > 0 and move_line.product_qty == 0:
                move_line.write({"product_qty": move_line.product_uom_qty})
        sale_order.picking_ids.button_validate()
