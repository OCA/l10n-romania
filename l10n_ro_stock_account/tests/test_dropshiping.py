# Copyright (C) 2024 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import Form, tagged

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install", "dropshipping")
class TestStockDropshipping(TestStockCommon):
    def _create_dropshipping_order(self, price_unit=150.0, vendor_price=80.0):
        # creare comanda de vanzre cu dropshiping
        so_form = Form(self.env["sale.order"])
        so_form.partner_id = self.client
        dropshipping_route = self.env.ref("stock_dropshipping.route_drop_shipping")
        self.product_1.write(
            {
                "standard_price": 100.0,
                "route_ids": [(4, dropshipping_route.id, 0)],
                "seller_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": self.vendor.id,
                            "price": vendor_price,
                        },
                    )
                ],
            }
        )

        with so_form.order_line.new() as so_line:
            so_line.product_id = self.product_1
            so_line.product_uom_qty = self.qty_so_p1
            so_line.price_unit = price_unit

        sale_order = so_form.save()
        sale_order.action_confirm()

        purchase = self.env["purchase.order"].search(
            [("partner_id", "=", self.vendor.id)], order="id desc", limit=1
        )
        purchase.button_confirm()

        picking = sale_order.picking_ids
        picking = sale_order.picking_ids
        is_dropshipped = picking._is_dropshipped()
        self.assertTrue(is_dropshipped, "Picking should be dropshipped")
        _is_dropshipped_returned = picking._is_dropshipped_returned()
        self.assertFalse(
            _is_dropshipped_returned, "Picking should not be dropshipped returned"
        )
        picking.action_assign()
        for move in picking.move_ids:
            move._set_quantity_done(move.product_uom_qty)
        picking.button_validate()

        return picking

    def test_dropshipping_without_408(self):
        """Test dropshipping FARA contul 408 configurat.
        Ar trebui sa avem SVL-uri, dar nota de receptie sa NU se genereze.
        """
        # Ne asiguram ca 408 NU este configurat pe companie
        self.env.company.l10n_ro_property_stock_picking_payable_account_id = False

        picking = self._create_dropshipping_order()

        svls = self.env["stock.valuation.layer"].search(
            [("stock_move_id", "in", picking.move_ids.ids)]
        )
        self.assertEqual(len(svls), 2, "Ar trebui sa avem 2 SVL-uri")

        for svl in svls:
            if svl.l10n_ro_valued_type == "reception":
                self.assertFalse(
                    svl.account_move_id,
                    "NU ar trebui sa avem note contabile pentru receptie "
                    "daca 408 nu e configurat",
                )
            elif svl.l10n_ro_valued_type == "delivery":
                self.assertTrue(
                    svl.account_move_id,
                    "Ar trebui sa avem in continuare note contabile pentru livrare",
                )
