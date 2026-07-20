# Copyright (C) 2020 Terrabit
# Copyright (C) 2025 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import os
from contextlib import closing

from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockFifo(TestROStockCommon):
    @classmethod
    @TestROStockCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.log_checks = False
        cls.l10n_ro_cost_type = "price_diff"
        cls.l10n_ro_approved_price_difference = True
        cls.env.company.l10n_ro_stock_acc_price_diff = True
        cls.product_dozen = cls.product_fifo.copy(
            {
                "name": "Product Dozen",
                "default_code": "product_dozen",
                "uom_id": cls.env.ref("uom.product_uom_dozen").id,
            }
        )
        cls.kg = cls.env.ref("uom.product_uom_kgm")
        cls.product_kg = cls.env["product.product"].create(
            {
                "name": "Product FIFO Kg",
                "is_storable": True,
                "categ_id": cls.category_marfa_fifo.id,
                "invoice_policy": "delivery",
                "purchase_method": "receive",
                "uom_id": cls.kg.id,
            }
        )

    def test_ro_stock_product_fifo(self):
        module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filename = "test_price_difference_fifo.csv"
        test_cases = self.read_test_cases_from_csv_file(filename, module_dir=module_dir)
        for _key, case in test_cases.items():
            _logger.info(
                "Running test case: %s - %s", case.get("code"), case.get("name")
            )
            with self.subTest(case=case), closing(self.cr.savepoint()):
                self.test_case(case)

    def _create_kg_reception(self, qty, price, partner_name):
        """Confirm and fully receive a purchase order for `self.product_kg`
        (a kg-based FIFO product). Returns (purchase, stock_move)."""
        partner = self.env["res.partner"].create({"name": partner_name})
        purchase = self.env["purchase.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_kg.id,
                            "product_qty": qty,
                            "product_uom_id": self.kg.id,
                            "price_unit": price,
                        },
                    )
                ],
            }
        )
        purchase.button_confirm()
        picking = purchase.picking_ids[0]
        picking.move_ids._set_quantity_done(qty)
        picking.move_ids.picked = True
        picking.button_validate()
        stock_move = purchase.order_line.move_ids.filtered(lambda m: m.state == "done")
        return purchase, stock_move

    def _create_invoice_line(self, purchase):
        """Create the vendor bill from the PO (draft) and return
        (invoice, invoice_line), with the invoice dates aligned on the PO."""
        action = purchase.action_create_invoice()
        invoice = self.env["account.move"].browse(action["res_id"])
        invoice_line = invoice.invoice_line_ids[0]
        invoice.invoice_date = purchase.date_order
        invoice.date = purchase.date_order
        invoice.invoice_date_due = purchase.date_order
        return invoice, invoice_line

    def _post_and_confirm(self, invoice):
        """Call the real action_post() (no approved-context bypass). If a
        confirmation wizard shows up, confirm it. Returns
        (wizard_appeared, confirm_succeeded)."""
        action = invoice.action_post()
        wizard_appeared = isinstance(action, dict)
        if not wizard_appeared:
            return False, True
        wizard = self.env["l10n_ro.price_difference_confirm_dialog"].browse(
            action["res_id"]
        )
        try:
            wizard.action_confirm()
        except Exception:
            return True, False
        return True, invoice.state == "posted"

    # -------------------------------------------------------------------
    # Base case: PO and bill match exactly (no quantity, no value
    # difference) - the wizard must never appear.
    # -------------------------------------------------------------------

    def test_ro_stock_price_difference_e2e_exact_match_no_wizard(self):
        purchase, _ = self._create_kg_reception(
            qty=100.0, price=10.0, partner_name="Vendor Exact Match"
        )
        invoice, _ = self._create_invoice_line(purchase)

        wizard_appeared, confirmed = self._post_and_confirm(invoice)

        self.assertFalse(
            wizard_appeared,
            "PO and bill matching exactly must never trigger the wizard",
        )
        self.assertTrue(confirmed)
        self.assertEqual(invoice.state, "posted")

    # -------------------------------------------------------------------
    # Value-only differences: quantity matches the PO/reception exactly,
    # only the price differs by the given amount. The wizard must appear
    # for any non-zero difference, and confirming it must succeed.
    # -------------------------------------------------------------------

    def test_ro_stock_price_difference_e2e_value_diff_confirms(self):
        for value_diff in (0.01, 0.5, -0.01, 50.0):
            with self.subTest(value_diff=value_diff):
                purchase, stock_move = self._create_kg_reception(
                    qty=100.0,
                    price=10.0,
                    partner_name=f"Vendor Value Diff {value_diff}",
                )
                stock_value = stock_move.value
                invoice, invoice_line = self._create_invoice_line(purchase)
                invoice_line.write({"price_unit": (stock_value + value_diff) / 100.0})

                wizard_appeared, confirmed = self._post_and_confirm(invoice)

                self.assertTrue(
                    wizard_appeared,
                    f"a {value_diff} lei value difference must trigger the wizard",
                )
                self.assertTrue(
                    confirmed,
                    f"a {value_diff} lei value-only difference must be confirmable",
                )
                self.assertEqual(invoice.state, "posted")

    # -------------------------------------------------------------------
    # Quantity-only differences: the true invoiced value still matches
    # what was received (price is recalculated so the total lines up), but
    # the quantity number itself differs by the given amount - the same
    # "wrong quantity, right total value" pattern an auto-matched EDI bill
    # produces. The wizard must appear (the reweight sees a value_diff
    # even though there's no real price difference); the open question is
    # whether confirming it succeeds or fails.
    # -------------------------------------------------------------------

    def test_ro_stock_price_difference_e2e_qty_diff_confirms(self):
        for qty_diff in (0.01, 0.5, -0.01, 50.0):
            with self.subTest(qty_diff=qty_diff):
                purchase, stock_move = self._create_kg_reception(
                    qty=100.0,
                    price=10.0,
                    partner_name=f"Vendor Qty Diff {qty_diff}",
                )
                stock_value = stock_move.value
                invoice, invoice_line = self._create_invoice_line(purchase)
                qty = 100.0 + qty_diff
                invoice_line.write({"quantity": qty, "price_unit": stock_value / qty})

                wizard_appeared, confirmed = self._post_and_confirm(invoice)

                self.assertTrue(
                    wizard_appeared,
                    f"a {qty_diff} kg quantity difference must trigger the wizard",
                )
                _logger.info(
                    "qty_diff=%s -> wizard_appeared=%s confirmed=%s invoice.state=%s",
                    qty_diff,
                    wizard_appeared,
                    confirmed,
                    invoice.state,
                )

    # -------------------------------------------------------------------
    # A product received in 3 separate lots (lot-valuated, each lot with
    # its own standard_price / valuation), invoiced at a different price
    # than the PO. Different valuation path than the plain FIFO cases
    # above (see stock_account's _set_value: lot_valuated products are
    # valued per move_line/lot, not via _run_fifo).
    # -------------------------------------------------------------------

    def test_ro_stock_price_difference_e2e_3_lots_value_diff_confirms(self):
        product = self.env["product.product"].create(
            {
                "name": "Product 3 Lots",
                "is_storable": True,
                "categ_id": self.category_marfa_fifo.id,
                "invoice_policy": "delivery",
                "purchase_method": "receive",
                "tracking": "lot",
                "lot_valuated": True,
            }
        )
        lots = self.env["stock.lot"].create(
            [{"name": f"3LOTS-{i}", "product_id": product.id} for i in range(1, 4)]
        )
        partner = self.env["res.partner"].create({"name": "Vendor 3 Lots"})

        purchase = self.env["purchase.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_qty": 3.0,
                            "price_unit": 10.0,
                        },
                    )
                ],
            }
        )
        purchase.button_confirm()
        picking = purchase.picking_ids[0]
        move = picking.move_ids
        move.move_line_ids.unlink()
        for lot in lots:
            self.env["stock.move.line"].create(
                {
                    "move_id": move.id,
                    "product_id": product.id,
                    "lot_id": lot.id,
                    "quantity": 1.0,
                    "location_id": move.location_id.id,
                    "location_dest_id": move.location_dest_id.id,
                    "picking_id": picking.id,
                }
            )
        move.picked = True
        picking.button_validate()

        stock_moves = purchase.order_line.move_ids.filtered(lambda m: m.state == "done")
        self.assertEqual(sum(stock_moves.mapped("value")), 30.0)

        action = purchase.action_create_invoice()
        invoice = self.env["account.move"].browse(action["res_id"])
        invoice_line = invoice.invoice_line_ids[0]
        # Same 3 units received, invoiced at 12/unit instead of the PO's
        # 10/unit: a real, unambiguous value difference (36 vs 30).
        invoice_line.write({"price_unit": 12.0})
        invoice.invoice_date = purchase.date_order
        invoice.date = purchase.date_order
        invoice.invoice_date_due = purchase.date_order

        wizard_appeared, confirmed = self._post_and_confirm(invoice)

        self.assertTrue(
            wizard_appeared,
            "a genuine value difference on a product split across 3 lots "
            "must trigger the confirmation wizard",
        )
        self.assertTrue(
            confirmed,
            "confirming a genuine value difference on a 3-lot reception must succeed",
        )
        self.assertEqual(invoice.state, "posted")
