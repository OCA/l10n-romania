# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile la achizitie

import logging
import random

from odoo.tests import Form
from odoo.tests.common import SavepointCase

_logger = logging.getLogger(__name__)


class TestStockCommon(SavepointCase):
    @classmethod
    def setUpAccounts(cls):
        def get_account(code):
            account = cls.env["account.account"].search([("code", "=", code)], limit=1)
            return account

        cls.account_difference = get_account("348000")
        cls.account_expense = get_account("607000")
        cls.account_expense_mp = get_account("601000")
        cls.account_income = get_account("707000")
        cls.account_valuation = get_account("371000")
        cls.account_valuation_mp = get_account("301000")

        cls.uneligible_tax_account_id = (
            cls.env.user.company_id.tax_cash_basis_journal_id.default_debit_account_id
        )
        if not cls.uneligible_tax_account_id:
            cls.uneligible_tax_account_id = get_account("442810")

        cls.env.user.company_id.tax_cash_basis_journal_id.default_debit_account_id = (
            cls.uneligible_tax_account_id
        )

        cls.stock_picking_payable_account_id = (
            cls.env.user.company_id.property_stock_picking_payable_account_id
        )
        if not cls.stock_picking_payable_account_id:
            cls.stock_picking_payable_account_id = get_account("408000")

        cls.env.user.company_id.property_stock_picking_payable_account_id = (
            cls.stock_picking_payable_account_id
        )

        cls.stock_picking_receivable_account_id = (
            cls.env.user.company_id.property_stock_picking_receivable_account_id
        )
        if not cls.stock_picking_receivable_account_id:
            cls.stock_picking_receivable_account_id = get_account("418000")

        cls.env.user.company_id.property_stock_picking_receivable_account_id = (
            cls.stock_picking_receivable_account_id
        )

        cls.stock_usage_giving_account_id = (
            cls.env.user.company_id.property_stock_usage_giving_account_id
        )
        if not cls.stock_usage_giving_account_id:
            cls.stock_usage_giving_account_id = get_account("803500")
            cls.env.user.company_id.property_stock_usage_giving_account_id = (
                cls.stock_usage_giving_account_id
            )

    @classmethod
    def setUpClass(cls):
        super(TestStockCommon, cls).setUpClass()

        cls.env.user.company_id.anglo_saxon_accounting = True
        cls.env.user.company_id.romanian_accounting = True
        cls.env.user.company_id.stock_acc_price_diff = True

        cls.setUpAccounts()

        stock_journal = cls.env["account.journal"].search(
            [("code", "=", "STJ"), ("company_id", "=", cls.env.user.company_id.id)],
            limit=1,
        )
        if not stock_journal:
            stock_journal = cls.env["account.journal"].create(
                {"name": "Stock Journal", "code": "STJ", "type": "general"}
            )

        acc_diff_id = cls.account_difference.id

        category_value = {
            "name": "TEST Marfa",
            "property_cost_method": "fifo",
            "property_valuation": "real_time",
            "property_account_creditor_price_difference_categ": acc_diff_id,
            "property_account_income_categ_id": cls.account_income.id,
            "property_account_expense_categ_id": cls.account_expense.id,
            "property_stock_account_input_categ_id": cls.account_valuation.id,
            "property_stock_account_output_categ_id": cls.account_valuation.id,
            "property_stock_valuation_account_id": cls.account_valuation.id,
            "property_stock_journal": stock_journal.id,
            "stock_account_change": True,
        }

        cls.category = cls.env["product.category"].search(
            [("name", "=", "TEST Marfa")], limit=1
        )
        if not cls.category:
            cls.category = cls.env["product.category"].create(category_value)
        else:
            cls.category.write(category_value)

        cls.category_mp = cls.category.copy(
            {
                "property_account_expense_categ_id": cls.account_expense_mp.id,
                "property_stock_account_input_categ_id": cls.account_valuation_mp.id,
                "property_stock_account_output_categ_id": cls.account_valuation_mp.id,
                "property_stock_valuation_account_id": cls.account_valuation_mp.id,
            }
        )

        cls.price_p1 = 50.0
        cls.price_p2 = round(random.random() * 100, 2)
        cls.list_price_p1 = 70.0
        cls.list_price_p2 = round(cls.price_p2 + random.random() * 50, 2)

        cls.product_1 = cls.env["product.product"].create(
            {
                "name": "Product A",
                "type": "product",
                "categ_id": cls.category.id,
                "invoice_policy": "delivery",
                "purchase_method": "receive",
                "list_price": cls.list_price_p1,
                "standard_price": cls.price_p1,
            }
        )
        cls.product_2 = cls.env["product.product"].create(
            {
                "name": "Product B",
                "type": "product",
                "purchase_method": "receive",
                "categ_id": cls.category.id,
                "invoice_policy": "delivery",
                "list_price": cls.list_price_p2,
                "standard_price": cls.price_p2,
            }
        )

        cls.product_mp = cls.env["product.product"].create(
            {
                "name": "Product MP",
                "type": "product",
                "categ_id": cls.category_mp.id,
                "invoice_policy": "delivery",
                "purchase_method": "receive",
                "list_price": cls.list_price_p1,
                "standard_price": cls.price_p1,
            }
        )

        cls.vendor = cls.env["res.partner"].search(
            [("name", "=", "TEST Vendor")], limit=1
        )
        if not cls.vendor:
            cls.vendor = cls.env["res.partner"].create({"name": "TEST Vendor"})

        cls.client = cls.env["res.partner"].search(
            [("name", "=", "TEST Client")], limit=1
        )
        if not cls.client:
            cls.client = cls.env["res.partner"].create({"name": "TEST Client"})

        cls.diff_p1 = 1
        cls.diff_p2 = -1

        # cantitatea din PO
        cls.qty_po_p1 = 20.0
        cls.qty_po_p2 = 20.0

        # cantitata din SO
        cls.qty_so_p1 = 5.0
        cls.qty_so_p2 = 5.0

        cls.val_p1_i = round(cls.qty_po_p1 * cls.price_p1, 2)
        cls.val_p2_i = round(cls.qty_po_p2 * cls.price_p2, 2)
        cls.val_p1_f = round(cls.qty_po_p1 * (cls.price_p1 + cls.diff_p1), 2)
        cls.val_p2_f = round(cls.qty_po_p2 * (cls.price_p2 + cls.diff_p2), 2)

        # valoarea descarcari de gestiune
        cls.val_stock_out_so_p1 = round(cls.qty_so_p1 * cls.price_p1, 2)
        cls.val_stock_out_so_p2 = round(cls.qty_so_p2 * cls.price_p2, 2)

        # valoarea vanzarii
        cls.val_so_p1 = round(cls.qty_so_p1 * cls.list_price_p1, 2)
        cls.val_so_p2 = round(cls.qty_so_p2 * cls.list_price_p2, 2)

        cls.val_p1_store = cls.qty_po_p1 * cls.list_price_p1
        cls.val_p2_store = cls.qty_po_p2 * cls.list_price_p2

        cls.tva_p1 = cls.val_p1_store * 0.19
        cls.tva_p2 = cls.val_p2_store * 0.19
        cls.val_p1_store = round(cls.val_p1_store + cls.tva_p1, 2)
        cls.val_p2_store = round(cls.val_p2_store + cls.tva_p2, 2)

        cls.adaos_p1 = round(cls.val_p1_store - cls.val_p1_i, 2)
        cls.adaos_p2 = round(cls.val_p2_store - cls.val_p2_i, 2)

        cls.adaos_p1_f = round(cls.val_p1_store - cls.val_p1_f, 2)
        cls.adaos_p2_f = round(cls.val_p2_store - cls.val_p2_f, 2)

        picking_type_in = cls.env.ref("stock.picking_type_in")
        location = picking_type_in.default_location_dest_id

        cls.location_warehouse = location.copy(
            {"merchandise_type": "warehouse", "name": "TEST warehouse"}
        )
        cls.picking_type_in_warehouse = picking_type_in.copy(
            {
                "default_location_dest_id": cls.location_warehouse.id,
                "name": "TEST Receptie in Depozit",
                "sequence_code": "IN_test",
            }
        )

        picking_type_transfer = cls.env.ref("stock.picking_type_internal")
        cls.picking_type_transfer = picking_type_transfer.copy(
            {
                "default_location_src_id": cls.location_warehouse.id,
                "default_location_dest_id": cls.location_warehouse.id,
                "name": "TEST Transfer",
                "sequence_code": "TR_test",
            }
        )
        domain = [
            ("usage", "=", "production"),
            ("company_id", "=", cls.env.user.company_id.id),
        ]
        cls.location_production = cls.env["stock.location"].search(domain, limit=1)

    def set_warehouse_as_mp(self):
        self.location_warehouse.write(
            {
                "property_stock_valuation_account_id": self.account_valuation_mp.id,
                "property_account_expense_location_id": self.account_expense_mp.id,
                "valuation_in_account_id": self.account_valuation_mp.id,
                "valuation_out_account_id": self.account_valuation_mp.id,
            }
        )

    def create_po(self, notice=False, picking_type_in=None):

        if not picking_type_in:
            picking_type_in = self.picking_type_in_warehouse

        po = Form(self.env["purchase.order"])
        po.partner_id = self.vendor
        po.picking_type_id = picking_type_in

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
        self.picking.write({"notice": notice})
        for move_line in self.picking.move_line_ids:
            if move_line.product_id == self.product_1:
                move_line.write({"qty_done": self.qty_po_p1})
            if move_line.product_id == self.product_2:
                move_line.write({"qty_done": self.qty_po_p2})

        self.picking.button_validate()
        self.picking.action_done()
        _logger.info("Receptie facuta")

        self.po = po
        return po

    def create_invoice(self, diff_p1=0, diff_p2=0):
        invoice = Form(self.env["account.move"].with_context(default_type="in_invoice"))
        invoice.partner_id = self.vendor
        invoice.purchase_id = self.po

        with invoice.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit += diff_p1
        with invoice.invoice_line_ids.edit(1) as line_form:
            line_form.price_unit += diff_p2

        invoice = invoice.save()

        invoice.post()

        _logger.info("Factura introdusa")

    def make_puchase(self):
        self.create_po()
        self.create_invoice()

    def make_return(self, pick, quantity=1.0):

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=pick.ids, active_id=pick.ids[0], active_model="stock.picking"
            )
        )
        return_wiz = stock_return_picking_form.save()
        return_wiz.product_return_moves.write({"quantity": quantity, "to_refund": True})
        res = return_wiz.create_returns()
        return_pick = self.env["stock.picking"].browse(res["res_id"])

        # Validate picking
        return_pick.action_confirm()
        return_pick.action_assign()
        for move_line in return_pick.move_lines:
            if move_line.product_uom_qty > 0 and move_line.quantity_done == 0:
                move_line.write({"quantity_done": move_line.product_uom_qty})
        return_pick.action_done()

    def trasfer(self, location, location_dest, product=None):

        self.PickingObj = self.env["stock.picking"]
        self.MoveObj = self.env["stock.move"]

        if not product:
            product = self.product_mp

        picking = self.PickingObj.create(
            {
                "picking_type_id": self.picking_type_transfer.id,
                "location_id": location.id,
                "location_dest_id": location_dest.id,
            }
        )
        self.MoveObj.create(
            {
                "name": product.name,
                "product_id": product.id,
                "product_uom_qty": 2,
                "product_uom": product.uom_id.id,
                "picking_id": picking.id,
                "location_id": location.id,
                "location_dest_id": location_dest.id,
            }
        )
        picking.action_confirm()
        picking.action_assign()
        for move_line in picking.move_lines:
            if move_line.product_uom_qty > 0 and move_line.quantity_done == 0:
                move_line.write({"quantity_done": move_line.product_uom_qty})
        picking.action_done()

        return picking

    def check_stock_valuation(self, val_p1, val_p2):
        val_p1 = round(val_p1, 2)
        val_p2 = round(val_p2, 2)
        domain = [("product_id", "in", [self.product_1.id, self.product_2.id])]
        valuations = self.env["stock.valuation.layer"].read_group(
            domain, ["value:sum", "quantity:sum"], ["product_id"]
        )

        for valuation in valuations:
            val = round(valuation["value"], 2)
            if valuation["product_id"][0] == self.product_1.id:
                _logger.info("Check stoc P1 {} = {}".format(val, val_p1))
                self.assertAlmostEqual(val, val_p1)
            if valuation["product_id"][0] == self.product_2.id:
                _logger.info("Check SVL P2 {} = {}".format(val, val_p2))
                self.assertAlmostEqual(val, val_p2)

    def check_account_valuation(self, val_p1, val_p2, account=None):
        val_p1 = round(val_p1, 2)
        val_p2 = round(val_p2, 2)
        if not account:
            account = self.account_valuation

        domain = [
            ("product_id", "in", [self.product_1.id, self.product_2.id]),
            ("account_id", "=", account.id),
        ]
        account_valuations = self.env["account.move.line"].read_group(
            domain, ["debit:sum", "credit:sum", "quantity:sum"], ["product_id"]
        )
        for valuation in account_valuations:
            val = round(valuation["debit"] - valuation["credit"], 2)
            if valuation["product_id"][0] == self.product_1.id:
                _logger.info("Check account P1 {} = {}".format(val, val_p1))
                self.assertAlmostEqual(val, val_p1)
            if valuation["product_id"][0] == self.product_2.id:
                _logger.info("Check account P2 {} = {}".format(val, val_p2))
                self.assertAlmostEqual(val, val_p2)

    def check_account_diff(self, val_p1, val_p2):
        self.check_account_valuation(val_p1, val_p2, self.account_difference)
