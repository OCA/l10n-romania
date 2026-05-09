# Copyright (C) 2024 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import Form, tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install", "dropshipping")
class TestStockDropshippingNotice(TestStockCommon):
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
        picking.l10n_ro_notice = True
        picking.action_assign()
        for move in picking.move_ids:
            move._set_quantity_done(move.product_uom_qty)
        picking.button_validate()

        return picking

    def test_dropshipping_with_408(self):
        """Test dropshipping cu contul 408 (facturi de primit) configurat.
        Ar trebui sa se genereze note contabile pentru receptie si livrare.
        """
        # Asiguram configurarea contului 408 pe companie
        self.env.company.l10n_ro_property_stock_picking_payable_account_id = (
            self.stock_picking_payable_account_id
        )

        picking = self._create_dropshipping_order()

        svls = self.env["stock.valuation.layer"].search(
            [("stock_move_id", "in", picking.move_ids.ids)]
        )
        self.assertEqual(
            len(svls), 2, "Ar trebui sa avem 2 SVL-uri (reception si delivery)"
        )

        for svl in svls:
            self.assertTrue(
                svl.account_move_id,
                "Ar trebui sa avem note contabile pentru SVL "
                f"{svl.l10n_ro_valued_type}",
            )
            am_lines = svl.account_move_id.line_ids
            debit_accounts = am_lines.filtered(lambda ln: ln.debit > 0).mapped(
                "account_id"
            )
            credit_accounts = am_lines.filtered(lambda ln: ln.credit > 0).mapped(
                "account_id"
            )

            if svl.l10n_ro_valued_type == "reception_notice":
                # Reception: Cont Gestiune (Debit) -> Cont 408 (Credit)
                self.assertIn(self.account_valuation, debit_accounts)
                self.assertIn(self.stock_picking_payable_account_id, credit_accounts)
            elif svl.l10n_ro_valued_type == "delivery_notice":
                # Delivery: Cont Cheltuiala (Debit) -> Cont Gestiune (Credit)
                self.assertIn(self.account_expense, debit_accounts)
                self.assertIn(self.account_valuation, credit_accounts)
