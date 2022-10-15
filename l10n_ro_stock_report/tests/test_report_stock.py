# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class TestStockReport(TransactionCase):
    def setUp(self):
        super(TestStockReport, self).setUp()
        self.env.company.write(
            {
                "l10n_ro_accounting": True,
                "anglo_saxon_accounting": True,
                "l10n_ro_stock_acc_price_diff": True,
            }
        )
        self.account_difference = self.env["account.account"].search(
            [("code", "=", "348000"), ("company_id", "=", self.env.company.id)]
        )
        self.account_expense = self.env["account.account"].search(
            [("code", "=", "607000"), ("company_id", "=", self.env.company.id)]
        )
        self.account_income = self.env["account.account"].search(
            [("code", "=", "707000"), ("company_id", "=", self.env.company.id)]
        )
        self.account_valuation = self.env["account.account"].search(
            [("code", "=", "371000"), ("company_id", "=", self.env.company.id)]
        )

        self.stock_journal = self.env["account.journal"].search(
            [("code", "=", "STJ"), ("company_id", "=", self.env.company.id)]
        )
        if not self.stock_journal:
            self.stock_journal = self.env["account.journal"].create(
                {"name": "Stock Journal", "code": "STJ", "type": "general"}
            )

        category_value = {
            "name": "TEST Marfa",
            "property_cost_method": "fifo",
            "property_valuation": "real_time",
            "property_account_creditor_price_difference_categ": self.account_difference.id,
            "property_account_income_categ_id": self.account_income.id,
            "property_account_expense_categ_id": self.account_expense.id,
            "property_stock_account_input_categ_id": self.account_valuation.id,
            "property_stock_account_output_categ_id": self.account_valuation.id,
            "property_stock_valuation_account_id": self.account_valuation.id,
            "property_stock_journal": self.stock_journal.id,
        }

        self.category = self.env["product.category"].search(
            [("name", "=", "TEST Marfa")]
        )
        if not self.category:
            self.category = self.env["product.category"].create(category_value)
        else:
            self.category.write(category_value)

        self.price_p1 = 50.0
        self.list_price_p1 = 70.0
        # cantitatea din PO
        self.qty_po_p1 = 20.0

        self.price_p2 = 40.0
        self.list_price_p2 = 60.0
        self.qty_po_p2 = 30.0

        self.product_1 = self.env["product.product"].create(
            {
                "name": "Product A",
                "type": "product",
                "categ_id": self.category.id,
                "invoice_policy": "delivery",
                "purchase_method": "receive",
                "list_price": self.list_price_p1,
                "standard_price": self.price_p1,
            }
        )

        self.product_2 = self.env["product.product"].create(
            {
                "name": "Product B",
                "type": "product",
                "categ_id": self.category.id,
                "invoice_policy": "delivery",
                "purchase_method": "receive",
                "list_price": self.list_price_p1,
                "standard_price": self.price_p1,
            }
        )

        Partner = self.env["res.partner"]
        self.vendor = Partner.search([("name", "=", "TEST Vendor")], limit=1)
        if not self.vendor:
            self.vendor = Partner.create({"name": "TEST Vendor"})

        self.client = Partner.search([("name", "=", "TEST Client")], limit=1)
        if not self.client:
            self.client = Partner.create({"name": "TEST Client"})

        picking_type_in = self.env.ref("stock.picking_type_in")
        self.location = picking_type_in.default_location_dest_id
        self.location_2 = self.env["stock.location"].create(
            {
                "name": "Location2",
                "usage": "internal",
                "location_id": self.location.id,
            }
        )

    def create_po(self, picking_type_in=None):
        po = Form(self.env["purchase.order"])
        po.partner_id = self.vendor

        with po.order_line.new() as po_line:
            po_line.product_id = self.product_1
            po_line.product_qty = self.qty_po_p1
            po_line.price_unit = self.price_p1
        with po.order_line.new() as po_line:
            po_line.product_id = self.product_2
            po_line.product_qty = self.qty_po_p2
            po_line.price_unit = self.price_p2

        po = po.save()
        po.button_confirm()
        self.picking = po.picking_ids[0]

        for move_line in self.picking.move_line_ids:
            if move_line.product_id == self.product_1:
                move_line.write({"qty_done": self.qty_po_p1})
            if move_line.product_id == self.product_2:
                move_line.write(
                    {"qty_done": self.qty_po_p2, "location_dest_id": self.location_2}
                )

        self.picking.button_validate()
        _logger.info("Receptie facuta")

        self.po = po
        return po

    def create_invoice(self):
        AccountMove = self.env["account.move"]
        invoice = Form(AccountMove.with_context(default_type="in_invoice"))
        invoice.partner_id = self.vendor
        invoice.purchase_id = self.po
        invoice = invoice.save()
        invoice.action_post()
        _logger.info("Factura introdusa")

    def test_report_storeage_sheet(self):
        self.create_po()
        self.create_invoice()

        wizard = Form(self.env["l10n.ro.stock.storage.sheet"])
        wizard.location_id = self.location
        wizard = wizard.save()

        wizard.button_show_sheet_pdf()
        line = self.env["l10n.ro.stock.storage.sheet.line"].search(
            [("report_id", "=", wizard.id)], limit=1
        )
        self.assertTrue(line)

    def test_get_products_with_move(self):
        stock_move_obj = self.env["stock.move"]
        products = (
            self.env["product.product"]
            .with_context(active_test=False)
            .search(
                [
                    ("type", "=", "product"),
                    "|",
                    ("company_id", "=", self.env.company.id),
                    ("company_id", "=", False),
                ]
            )
        )
        wizard = Form(self.env["l10n.ro.stock.storage.sheet"])
        wizard.location_id = self.location
        wizard.products_with_move = True
        wizard = wizard.save()

        prod_with_moves = (
            stock_move_obj.with_context(active_test=False)
            .search(
                [
                    ("state", "=", "done"),
                    ("date", ">=", wizard.date_from),
                    ("date", "<=", wizard.date_to),
                    ("product_id", "in", products.ids),
                    "|",
                    ("location_id", "=", self.location.id),
                    ("location_dest_id", "=", self.location.id),
                ]
            )
            .mapped("product_id")
            .filtered(lambda p: p.type == "product")
        )
        exp_prod_list = wizard.get_products_with_move()
        self.assertEqual(exp_prod_list, [])
        exp_found_prod = wizard.get_found_products()
        self.assertEqual(exp_found_prod, prod_with_moves)

        wizard_no_moves = Form(self.env["l10n.ro.stock.storage.sheet"])
        wizard_no_moves.location_id = self.location
        wizard_no_moves.products_with_move = False
        wizard_no_moves = wizard_no_moves.save()
        exp_found_prod = wizard_no_moves.get_found_products()
        self.assertEqual(exp_found_prod, products)

        exp_product = products[1]  # index 0 is archived
        wizard_product = Form(self.env["l10n.ro.stock.storage.sheet"])
        wizard_product.location_id = self.location
        wizard_product.products_with_move = False
        wizard_product = wizard_product.save()
        wizard_product.product_ids = [(6, 0, exp_product.ids)]
        exp_found_prod = wizard_product.get_found_products()
        self.assertEqual(exp_found_prod, exp_product)

        exp_product = [products - prod_with_moves][0]
        wizard_product = Form(self.env["l10n.ro.stock.storage.sheet"])
        wizard_product.location_id = self.location
        wizard_product = wizard_product.save()
        wizard_product.product_ids = [(6, 0, exp_product.ids)]
        with self.assertRaises(UserError):
            wizard_product.get_found_products()

    def test_report_storeage_sheet_sublocation(self):
        self.create_po()
        self.create_invoice()

        wizard = Form(self.env["l10n.ro.stock.storage.sheet"])
        wizard.location_id = self.location
        wizard.sublocation = True
        wizard = wizard.save()

        wizard.button_show_sheet_pdf()
        line = self.env["l10n.ro.stock.storage.sheet.line"].search(
            [("report_id", "=", wizard.id), ("location_id", "=", self.location_2.id)],
            limit=1,
        )
        self.assertTrue(line)

    def test_report_with_stock_landed_costs(self):
        self.env.company.anglo_saxon_accounting = True
        # Create PO with Product A
        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.vendor
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product_1
            po_line.product_qty = 1
            po_line.price_unit = 70.0
        po_form = po_form.save()
        po_form.button_confirm()

        # Receive the goods
        receipt = po_form.picking_ids[0]
        receipt.move_line_ids.qty_done = 1
        receipt.button_validate()

        # Check SVL
        svl = self.env["stock.valuation.layer"].search(
            [("stock_move_id", "=", receipt.move_lines.id)]
        )
        self.assertAlmostEqual(svl.value, 70)

        # copy svl dand modify the quantity
        svl2 = svl.copy()
        svl2.quantity = 0
        svl2.unit_cost = 0
        svl2.value = 20

        wizard = Form(self.env["l10n.ro.stock.storage.sheet"])
        wizard.location_id = self.location
        wizard = wizard.save()

        wizard.button_show_sheet_pdf()
        line = self.env["l10n.ro.stock.storage.sheet.line"].search(
            [("report_id", "=", wizard.id), ("product_id", "=", self.product_1.id)]
        )
        self.assertEqual(sum(line.mapped("amount_initial")), 0)
        self.assertEqual(sum(line.mapped("quantity_initial")), 0)
        self.assertEqual(sum(line.mapped("amount_in")), 90)
        self.assertEqual(sum(line.mapped("quantity_in")), 1)
        self.assertEqual(sum(line.mapped("amount_out")), 0)
        self.assertEqual(sum(line.mapped("quantity_out")), 0)
        self.assertEqual(sum(line.mapped("amount_final")), 90)
        self.assertEqual(sum(line.mapped("quantity_final")), 1)
