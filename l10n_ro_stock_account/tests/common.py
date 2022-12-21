# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile la achizitie

import logging

from odoo import fields
from odoo.tests import Form, tagged

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import (
    ValuationReconciliationTestCommon,
)

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockCommon(ValuationReconciliationTestCommon):
    @classmethod
    def setUpAccounts(cls):
        def get_account(code):
            account = cls.env["account.account"].search([("code", "=", code)], limit=1)
            return account

        cls.account_difference = get_account("378000")
        cls.account_expense = get_account("607000")
        cls.account_expense_mp = get_account("601000")
        cls.account_income = get_account("707000")
        cls.account_valuation = get_account("371000")
        cls.account_valuation_mp = get_account("301000")

        cls.uneligible_tax_account_id = (
            cls.env.user.company_id.tax_cash_basis_journal_id.default_account_id
        )
        if not cls.uneligible_tax_account_id:
            cls.uneligible_tax_account_id = get_account("442810")

        cls.env.user.company_id.tax_cash_basis_journal_id.default_account_id = (
            cls.uneligible_tax_account_id
        )

        cls.stock_picking_payable_account_id = (
            cls.env.user.company_id.l10n_ro_property_stock_picking_payable_account_id
        )
        if not cls.stock_picking_payable_account_id:
            cls.stock_picking_payable_account_id = get_account("408000")

        cls.env.user.company_id.l10n_ro_property_stock_picking_payable_account_id = (
            cls.stock_picking_payable_account_id
        )

        cls.stock_picking_receivable_account_id = (
            cls.env.user.company_id.l10n_ro_property_stock_picking_receivable_account_id
        )
        if not cls.stock_picking_receivable_account_id:
            cls.stock_picking_receivable_account_id = get_account("418000")

        cls.env.user.company_id.l10n_ro_property_stock_picking_receivable_account_id = (
            cls.stock_picking_receivable_account_id
        )

        cls.stock_usage_giving_account_id = (
            cls.env.user.company_id.l10n_ro_property_stock_usage_giving_account_id
        )
        if not cls.stock_usage_giving_account_id:
            cls.stock_usage_giving_account_id = get_account("803500")
            cls.env.user.company_id.l10n_ro_property_stock_usage_giving_account_id = (
                cls.stock_usage_giving_account_id
            )

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        ro_template_ref = "l10n_ro.ro_chart_template"
        super(TestStockCommon, cls).setUpClass(chart_template_ref=ro_template_ref)

        cls.env.company.anglo_saxon_accounting = True
        cls.env.company.l10n_ro_accounting = True
        cls.env.company.l10n_ro_stock_acc_price_diff = True

        cls.setUpAccounts()

        stock_journal = cls.env["account.journal"].search(
            [("code", "=", "STJ"), ("company_id", "=", cls.env.company.id)],
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
            "l10n_ro_stock_account_change": True,
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
        cls.price_p2 = 50.0
        cls.list_price_p1 = 70.0
        cls.list_price_p2 = 70.0

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
        cls.qty_po_p1 = 10.0
        cls.qty_po_p2 = 10.0

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

        # valoarea descarcari de gestiune incluzand si diferentele
        cls.val_stock_out_so_p1_diff = round(
            cls.val_stock_out_so_p1 + (cls.qty_so_p1 * cls.diff_p1), 2
        )
        cls.val_stock_out_so_p2_diff = round(
            cls.val_stock_out_so_p2 + (cls.qty_so_p2 * cls.diff_p2), 2
        )

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

        warehouse = cls.company_data["default_warehouse"]

        picking_type_in = warehouse.in_type_id
        location = picking_type_in.default_location_dest_id
        # Locatia trebuie sa fie child la Stock, altfel la livrari
        # foloseste location Stock implicita
        cls.location_warehouse = location.copy(
            {
                "l10n_ro_merchandise_type": "warehouse",
                "name": "TEST warehouse",
                "location_id": location.id,
            }
        )
        cls.picking_type_in_warehouse = picking_type_in.copy(
            {
                "default_location_dest_id": cls.location_warehouse.id,
                "name": "TEST Receptie in Depozit",
                "sequence_code": "IN_test",
            }
        )
        picking_type_out = warehouse.out_type_id
        cls.picking_type_out_warehouse = picking_type_out.copy(
            {
                "default_location_src_id": cls.location_warehouse.id,
                "name": "TEST Livrare in Depozit",
                "sequence_code": "OUT_test",
            }
        )
        picking_type_transfer = warehouse.int_type_id
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
                "l10n_ro_property_stock_valuation_account_id": self.account_valuation_mp.id,
                "l10n_ro_property_account_expense_location_id": self.account_expense_mp.id,
                "valuation_in_account_id": self.account_valuation_mp.id,
                "valuation_out_account_id": self.account_valuation_mp.id,
            }
        )

    def writeOnPicking(self, vals=False):
        if not vals:
            vals = {}
        self.picking.write(vals)

    def create_po(
        self, picking_type_in=None, partial=None, vals=False, validate_picking=True
    ):

        if not picking_type_in:
            picking_type_in = self.picking_type_in_warehouse
        if not partial or (partial and not hasattr(self, "po")):
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
        else:
            po = self.po

        if validate_picking:
            self.picking = po.picking_ids.filtered(lambda pick: pick.state != "done")
            self.writeOnPicking(vals)
            qty_po_p1 = self.qty_po_p1 if not partial else self.qty_po_p1 / 2
            qty_po_p2 = self.qty_po_p2 if not partial else self.qty_po_p2 / 2
            for move_line in self.picking.move_line_ids:
                if move_line.product_id == self.product_1:
                    move_line.write({"qty_done": qty_po_p1})
                if move_line.product_id == self.product_2:
                    move_line.write({"qty_done": qty_po_p2})

            self.picking.button_validate()
            self.picking._action_done()
            _logger.info("Receptie facuta")

        self.po = po
        return po

    def create_invoice(
        self, diff_p1=0, diff_p2=0, quant_p1=0, quant_p2=0, auto_post=True
    ):
        invoice = Form(
            self.env["account.move"].with_context(
                default_move_type="in_invoice",
                default_invoice_date=fields.Date.today(),
                active_model="accoun.move",
            )
        )
        invoice.partner_id = self.vendor
        invoice.purchase_id = self.po

        with invoice.invoice_line_ids.edit(0) as line_form:
            line_form.quantity += quant_p1
            line_form.price_unit += diff_p1
        with invoice.invoice_line_ids.edit(1) as line_form:
            line_form.quantity += quant_p2
            line_form.price_unit += diff_p2

        invoice = invoice.save()
        if invoice.amount_total < 0:
            invoice.action_switch_invoice_into_refund_credit_note()
        if quant_p1 or quant_p2 or diff_p1 or diff_p2:
            invoice = invoice.with_context(l10n_ro_approved_price_difference=True)
        if auto_post:
            invoice.action_post()

        self.invoice = invoice
        _logger.debug("Factura introdusa")

    def make_purchase(self):
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
        return_pick._action_done()

    def create_so(self, vals=False):
        _logger.debug("Start sale")
        so = Form(self.env["sale.order"])
        so.partner_id = self.client

        with so.order_line.new() as so_line:
            so_line.product_id = self.product_1
            so_line.product_uom_qty = self.qty_so_p1
            # so_line.price_unit = self.p

        with so.order_line.new() as so_line:
            so_line.product_id = self.product_2
            so_line.product_uom_qty = self.qty_so_p2

        self.so = so.save()
        self.so.action_confirm()
        self.picking = self.so.picking_ids
        self.writeOnPicking(vals)
        self.picking.action_assign()  # verifica disponibilitate

        for move_line in self.picking.move_lines:
            if move_line.product_uom_qty > 0 and move_line.quantity_done == 0:
                move_line.write({"quantity_done": move_line.product_uom_qty})

        # self.picking.move_lines.write({'quantity_done': 2})
        # self.picking.button_validate()
        self.picking._action_done()
        _logger.debug("Livrare facuta")
        return self.picking

    def create_sale_invoice(self, diff_p1=0, diff_p2=0):
        # invoice on order
        invoice = self.so._create_invoices()

        invoice = Form(invoice)

        with invoice.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit += diff_p1
        with invoice.invoice_line_ids.edit(1) as line_form:
            line_form.price_unit += diff_p2

        invoice = invoice.save()

        invoice.action_post()

    def transfer(
        self, location, location_dest, product=False, accounting_date=False, post=True
    ):

        self.PickingObj = self.env["stock.picking"]
        self.MoveObj = self.env["stock.move"]
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
        if accounting_date:
            picking.l10n_ro_accounting_date = accounting_date
        picking.action_confirm()
        picking.action_assign()
        if post:
            for move_line in picking.move_lines:
                if move_line.product_uom_qty > 0 and move_line.quantity_done == 0:
                    move_line.write({"quantity_done": move_line.product_uom_qty})
            picking._action_done()
        self.picking = picking

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
                _logger.debug("Check stock P1 {} = {}".format(val, val_p1))
                self.assertAlmostEqual(val, val_p1)
            if valuation["product_id"][0] == self.product_2.id:
                _logger.debug("Check stock P2 {} = {}".format(val, val_p2))
                self.assertAlmostEqual(val, val_p2)

    def check_account_valuation(self, val_p1, val_p2, account=None):
        val_p1 = round(val_p1, 2)
        val_p2 = round(val_p2, 2)
        if not account:
            account = self.account_valuation

        domain = [
            ("product_id", "in", [self.product_1.id, self.product_2.id]),
            ("account_id", "=", account.id),
            ("parent_state", "=", "posted"),
        ]
        account_valuations = self.env["account.move.line"].read_group(
            domain, ["debit:sum", "credit:sum", "quantity:sum"], ["product_id"]
        )
        for valuation in account_valuations:
            val = round(valuation["debit"] - valuation["credit"], 2)
            if valuation["product_id"][0] == self.product_1.id:
                _logger.debug("Check account P1 {} = {}".format(val, val_p1))
                self.assertAlmostEqual(val, val_p1)
            if valuation["product_id"][0] == self.product_2.id:
                _logger.debug("Check account P2 {} = {}".format(val, val_p2))
                self.assertAlmostEqual(val, val_p2)

    def check_account_diff(self, val_p1, val_p2):
        self.check_account_valuation(val_p1, val_p2, self.account_difference)

    def check_account_valuation_mp(self, val_p1, account=None):
        val_p1 = round(val_p1, 2)
        if not account:
            account = self.account_valuation

        domain = [
            ("product_id", "=", self.product_mp.id),
            ("account_id", "=", account.id),
            ("parent_state", "=", "posted"),
        ]
        account_valuations = self.env["account.move.line"].read_group(
            domain, ["debit:sum", "credit:sum", "quantity:sum"], ["product_id"]
        )
        for valuation in account_valuations:
            val = round(valuation["debit"] - valuation["credit"], 2)
            if valuation["product_id"][0] == self.product_mp.id:
                _logger.info("Check account P1 {} = {}".format(val, val_p1))
                self.assertAlmostEqual(val, val_p1)

    def set_stock(self, product, qty, location=None):
        if not location:
            location = self.location_warehouse
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": product.id,
                "inventory_quantity": qty,
                "location_id": location.id,
            }
        )

    def _get_stock_valuation_move_lines(self):
        return self.env["account.move.line"].search(
            [
                ("account_id", "=", self.account_valuation.id),
            ],
            order="date, id",
        )

    def _get_stock_output_move_lines(self):
        return self.env["account.move.line"].search(
            [
                ("account_id", "=", self.account_expense.id),
            ],
            order="date, id",
        )
