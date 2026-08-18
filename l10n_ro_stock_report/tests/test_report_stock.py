# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from datetime import timedelta

from odoo import fields
from odoo.tests import Form
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class TestStockReport(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.company.write(
            {
                "l10n_ro_accounting": True,
                "anglo_saxon_accounting": True,
                "l10n_ro_stock_acc_price_diff": True,
            }
        )
        AccountAccount = self.env["account.account"]

        def get_or_create_account(code, name, account_type):
            account = AccountAccount.search(
                [
                    ("code", "=", code),
                ],
                limit=1,
            )
            if not account:
                account = AccountAccount.create(
                    {
                        "code": code,
                        "name": name,
                        "account_type": account_type,
                        "company_ids": [(4, self.env.company.id)],
                    }
                )
            return account

        self.account_difference = get_or_create_account(
            "348000", "Price Difference", "asset_current"
        )
        self.account_expense = get_or_create_account(
            "607000", "Cost of Goods Sold", "expense"
        )
        self.account_income = get_or_create_account("707000", "Revenue", "income")
        self.account_valuation = get_or_create_account(
            "371000", "Stock Valuation", "asset_current"
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
            "property_account_income_categ_id": self.account_income.id,
            "property_account_expense_categ_id": self.account_expense.id,
            "property_stock_valuation_account_id": self.account_valuation.id,
            "property_stock_journal": self.stock_journal.id,
            "l10n_ro_stock_account_change": True,
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
                "is_storable": True,
                "categ_id": self.category.id,
                "list_price": self.list_price_p1,
                "standard_price": self.price_p1,
            }
        )

        self.product_2 = self.env["product.product"].create(
            {
                "name": "Product B",
                "is_storable": True,
                "categ_id": self.category.id,
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
                move_line.write({"quantity": self.qty_po_p1})
            if move_line.product_id == self.product_2:
                move_line.write(
                    {"quantity": self.qty_po_p2, "location_dest_id": self.location_2.id}
                )
                move_line.move_id.write({"location_dest_id": self.location_2.id})

        self.picking.button_validate()
        _logger.debug("Receptie facuta")

        self.po = po
        return po

    def create_invoice(self):
        action = self.po.action_create_invoice()
        invoice = self.env["account.move"].browse(action["res_id"])
        invoice.invoice_date = fields.Date.today()
        invoice.action_post()
        # _logger.info("Factura introdusa")

    def test_report_storage_sheet(self):
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

        domain = [
            ("is_storable", "=", True),
            "|",
            ("company_id", "=", self.env.company.id),
            ("company_id", "=", False),
        ]
        products = (
            self.env["product.product"].with_context(active_test=False).search(domain)
        )

        self._create_receipt(self.product_1, 1, fields.Datetime.now())

        wizard = Form(self.env["l10n.ro.stock.storage.sheet"])
        wizard.location_id = self.location
        wizard.products_with_move = True
        wizard = wizard.save()

        prod_with_moves = (
            stock_move_obj.with_context(active_test=False)
            .search(
                [
                    ("state", "=", "done"),
                    ("date", "<=", wizard.date_to),
                    ("product_id", "in", products.ids),
                    "|",
                    ("location_id", "in", wizard.location_ids.ids),
                    ("location_dest_id", "in", wizard.location_ids.ids),
                ]
            )
            .mapped("product_id")
            .filtered(lambda p: p.is_storable)
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
        # with self.assertRaises(UserError):
        #     wizard_product.get_found_products()

    def test_report_storage_sheet_sublocation(self):
        self.create_po()
        self.create_invoice()

        wizard = Form(self.env["l10n.ro.stock.storage.sheet"])
        wizard.location_id = self.location
        wizard.sublocation = True
        wizard.detailed_locations = True
        wizard = wizard.save()

        wizard.button_show_sheet_pdf()
        line = self.env["l10n.ro.stock.storage.sheet.line"].search(
            [("report_id", "=", wizard.id), ("location_id", "=", self.location_2.id)],
            limit=1,
        )
        self.assertTrue(line)

    def test_report_storage_sheet_sublocation2(self):
        self.create_po()
        self.create_invoice()

        wizard = Form(self.env["l10n.ro.stock.storage.sheet"])
        wizard.location_id = self.location
        wizard.sublocation = True
        wizard.detailed_locations = False
        wizard = wizard.save()

        wizard.button_show_sheet_pdf()
        line = self.env["l10n.ro.stock.storage.sheet.line"].search(
            [("report_id", "=", wizard.id), ("location_id", "=", self.location.id)],
            limit=1,
        )
        self.assertTrue(line)

    def _create_simple_picking(self, picking_type, product, qty, date_dt):
        Picking = self.env["stock.picking"]
        Move = self.env["stock.move"]

        picking = Picking.create(
            {
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
                "scheduled_date": date_dt,
            }
        )
        Move.create(
            {
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": qty,
                "picking_id": picking.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "date": date_dt,
                "company_id": self.env.company.id,
            }
        )
        picking.action_confirm()

        picking.button_validate()
        # Ensure the move date matches the intended period for reporting
        for m in picking.move_ids:
            m.date = date_dt
        return picking

    def _create_receipt(self, product, qty, date_dt):
        picking_type_in = self.env.ref("stock.picking_type_in")
        return self._create_simple_picking(picking_type_in, product, qty, date_dt)

    def _create_delivery(self, product, qty, date_dt):
        picking_type_out = self.env.ref("stock.picking_type_out")
        return self._create_simple_picking(picking_type_out, product, qty, date_dt)

    def test_report_two_periods_quantities(self):
        """
        Scenario requested:
        - On date1: purchase 4, sale 2 → report: init 0, in 4, out 2, final 2
        - On later date2: purchase 10, sale 4 → report: init 2, in 10, out 4, final 8
        """
        product = self.product_1
        # Use stable past dates to avoid timezone boundary issues
        date1_dt = fields.Datetime.now() - timedelta(days=25)
        data1_from = fields.Datetime.now() - timedelta(days=30)
        data1_to = fields.Datetime.now() - timedelta(days=20)

        date2_dt = fields.Datetime.now() - timedelta(days=10)
        data2_from = fields.Datetime.now() - timedelta(days=15)
        data2_to = fields.Datetime.now() - timedelta(days=1)

        # Period 1 operations
        self._create_receipt(product, 4, date1_dt)
        self._create_delivery(product, 2, date1_dt)

        # Report for period 1
        wizard1 = Form(self.env["l10n.ro.stock.storage.sheet"])
        wizard1.location_id = self.location
        wizard1.product_ids = product
        wizard1.date_from = data1_from.date()
        wizard1.date_to = data1_to.date()
        wizard1 = wizard1.save()
        wizard1.button_show_sheet_pdf()

        lines1 = self.env["l10n.ro.stock.storage.sheet.line"].search(
            [
                ("report_id", "=", wizard1.id),
                ("product_id", "=", product.id),
                ("location_id", "=", self.location.id),
            ]
        )

        qty_init_1 = sum(lines1.mapped("quantity_initial"))
        qty_in_1 = sum(lines1.mapped("quantity_in"))
        qty_out_1 = sum(lines1.mapped("quantity_out"))
        qty_final_1 = sum(lines1.mapped("quantity_final"))
        self.assertEqual(qty_init_1, 0)
        self.assertEqual(qty_in_1, 4)
        self.assertEqual(qty_out_1, 2)
        self.assertEqual(qty_final_1, 2)

        # Period 2 operations
        self._create_receipt(product, 10, date2_dt)
        self._create_delivery(product, 4, date2_dt)

        # Report for period 2
        wizard2 = Form(self.env["l10n.ro.stock.storage.sheet"])
        wizard2.location_id = self.location
        wizard2.product_ids = product
        wizard2.date_from = data2_from.date()
        wizard2.date_to = data2_to.date()
        wizard2 = wizard2.save()
        wizard2.button_show_sheet_pdf()

        lines2 = self.env["l10n.ro.stock.storage.sheet.line"].search(
            [
                ("report_id", "=", wizard2.id),
                ("product_id", "=", product.id),
                ("location_id", "=", self.location.id),
            ]
        )
        qty_init_2 = sum(lines2.mapped("quantity_initial"))
        qty_in_2 = sum(lines2.mapped("quantity_in"))
        qty_out_2 = sum(lines2.mapped("quantity_out"))
        qty_final_2 = sum(lines2.mapped("quantity_final"))
        self.assertEqual(qty_init_2, 2)
        self.assertEqual(qty_in_2, 10)
        self.assertEqual(qty_out_2, 4)
        self.assertEqual(qty_final_2, 8)

    def test_report_valued_type_from_move_type(self):
        """The valued type of a movement line comes from the move type.

        Up to 18.0 it was read from the valuation layer; since that layer is gone
        in 19.0 the report has to read stock.move.l10n_ro_move_type, otherwise
        every line falls into a single "Indefinite" group.
        """
        product = self.product_1
        date_dt = fields.Datetime.now() - timedelta(days=5)
        date_from = fields.Datetime.now() - timedelta(days=10)
        date_to = fields.Datetime.now() - timedelta(days=1)

        receipt = self._create_receipt(product, 6, date_dt)
        delivery = self._create_delivery(product, 2, date_dt)
        self.assertEqual(receipt.move_ids.l10n_ro_move_type, "reception")
        self.assertEqual(delivery.move_ids.l10n_ro_move_type, "delivery")

        wizard = Form(self.env["l10n.ro.stock.storage.sheet"])
        wizard.location_id = self.location
        wizard.product_ids = product
        wizard.date_from = date_from.date()
        wizard.date_to = date_to.date()
        wizard = wizard.save()
        wizard.button_show_sheet_pdf()

        lines = self.env["l10n.ro.stock.storage.sheet.line"].search(
            [
                ("report_id", "=", wizard.id),
                ("product_id", "=", product.id),
                ("location_id", "=", self.location.id),
            ]
        )
        lines_in = lines.filtered(lambda line: line.quantity_in)
        lines_out = lines.filtered(lambda line: line.quantity_out)
        self.assertTrue(lines_in)
        self.assertTrue(lines_out)
        self.assertEqual(set(lines_in.mapped("valued_type")), {"reception"})
        self.assertEqual(set(lines_out.mapped("valued_type")), {"delivery"})

        # Movement types must be part of the selection, otherwise the values
        # cannot be grouped nor read in the user interface.
        selection = dict(
            self.env["l10n.ro.stock.storage.sheet.line"]
            ._fields["valued_type"]
            .selection
        )
        self.assertIn("reception", selection)
        self.assertIn("delivery", selection)
        self.assertIn("indefinite", selection)

    def test_report_balance_lines_have_own_valued_type(self):
        """The opening and closing balance lines carry their own valued type.

        The balances are not movements, so they have no move type to read. When
        they are left without a valued type they land in the same empty-type
        group as the movements of unknown type, and that group then shows an
        opening balance differing from the closing balance with no movement in
        between - the movements sitting on the typed rows instead. Every figure
        is correct, but the sheet reads as broken.
        """
        product = self.product_1
        date_dt = fields.Datetime.now() - timedelta(days=5)
        date_from = fields.Datetime.now() - timedelta(days=10)
        date_to = fields.Datetime.now() - timedelta(days=1)

        self._create_receipt(product, 6, date_dt)
        self._create_delivery(product, 2, date_dt)

        wizard = Form(self.env["l10n.ro.stock.storage.sheet"])
        wizard.location_id = self.location
        wizard.product_ids = product
        wizard.date_from = date_from.date()
        wizard.date_to = date_to.date()
        wizard = wizard.save()
        wizard.button_show_sheet_pdf()

        lines = self.env["l10n.ro.stock.storage.sheet.line"].search(
            [
                ("report_id", "=", wizard.id),
                ("product_id", "=", product.id),
                ("location_id", "=", self.location.id),
            ]
        )
        self.assertTrue(lines)

        # No report line may be left without a valued type: that is the bucket
        # the balances used to fall into.
        self.assertNotIn(
            False,
            lines.mapped("valued_type"),
            "Every storage sheet line must carry a valued type",
        )

        final_lines = lines.filtered(lambda line: line.valued_type == "final")
        self.assertTrue(final_lines, "The closing balance line must be typed 'final'")
        # Receipt of 6 less delivery of 2 left on hand at the end of the period.
        self.assertEqual(sum(final_lines.mapped("quantity_final")), 4)

        # The balance types must be part of the selection, otherwise the values
        # cannot be grouped nor read in the user interface.
        selection = dict(
            self.env["l10n.ro.stock.storage.sheet.line"]
            ._fields["valued_type"]
            .selection
        )
        self.assertIn("initial", selection)
        self.assertIn("final", selection)
