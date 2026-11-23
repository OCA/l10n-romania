# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Delivery on notice (418 = 707) with a price-included sale tax and a discount.

The notice books the revenue now and the invoice reverses 418 later: both have
to use the same amount, the untaxed and discounted one, or 418 keeps the VAT.
"""

from odoo.tests import tagged

from .common import TestROStockCommon


@tagged("post_install", "-at_install")
class TestNoticeDeliveryUntaxed(TestROStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The company's own sale tax (with its VAT account), price-included.
        cls.tax_included = cls.env.company.account_sale_tax_id.copy(
            {"name": "TVA inclus (test)", "price_include_override": "tax_included"}
        )
        cls.product_fifo.taxes_id = cls.tax_included
        cls.acc_418 = (
            cls.env.company.l10n_ro_property_stock_picking_receivable_account_id
        )

    def _deliver_on_notice(self, qty, price, discount=0.0):
        self._receive(10, 50, 1)
        so = self.env["sale.order"].create(
            {
                "partner_id": self.customer_1.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_fifo.id,
                            "product_uom_qty": qty,
                            "price_unit": price,
                            "discount": discount,
                            "tax_ids": [(6, 0, self.tax_included.ids)],
                        },
                    )
                ],
            }
        )
        so.action_confirm()
        picking = so.picking_ids
        picking.l10n_ro_notice = True
        picking.move_ids._set_quantity_done(qty)
        picking.move_ids.picked = True
        picking.button_validate()
        return so, picking.move_ids

    def _418(self):
        return sum(
            self.env["account.move.line"]
            .search(
                [
                    ("account_id", "=", self.acc_418.id),
                    ("parent_state", "=", "posted"),
                ]
            )
            .mapped("balance")
        )

    def test_notice_revenue_is_untaxed_and_discounted(self):
        so, move = self._deliver_on_notice(5, 121.0, discount=10.0)
        self.assertEqual(move.l10n_ro_move_type, "delivery_notice")
        # 121 with 21 % VAT included is 100 without; less 10 % is 90; times 5.
        self.assertAlmostEqual(self._418(), 450.0, places=2)

    def test_invoice_closes_418(self):
        so, _move = self._deliver_on_notice(5, 121.0, discount=10.0)
        invoice = so._create_invoices()
        invoice.action_post()
        self.assertAlmostEqual(invoice.amount_untaxed, 450.0, places=2)
        self.assertAlmostEqual(self._418(), 0.0, places=2)
