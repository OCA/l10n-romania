# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from datetime import timedelta

from odoo import fields
from odoo.tests import Form, tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockReport(TestROStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        def get_account(code):
            account = cls.env["account.account"].search([("code", "=", code)], limit=1)
            if not account:
                _logger.error(f"Account {code} not found")
            return account

        stock_journal = cls.env["account.journal"].search(
            [("code", "=", "STJ"), ("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        if not stock_journal:
            stock_journal = cls.env["account.journal"].create(
                {"name": "Stock Journal", "code": "STJ", "type": "general"}
            )

        category_value = {
            "name": "TEST Marfa",
            "property_cost_method": "fifo",
            "property_valuation": "real_time",
            "property_account_income_categ_id": cls.account_income.id,
            "property_account_expense_categ_id": cls.account_expense.id,
            "property_stock_valuation_account_id": cls.account_valuation.id,
            "property_stock_journal": stock_journal.id,
            "l10n_ro_stock_account_change": True,
        }

        cls.category_fifo = cls.env["product.category"].search(
            [("name", "=", "TEST Marfa")], limit=1
        )
        if not cls.category_fifo:
            cls.category_fifo = cls.env["product.category"].create(category_value)
        else:
            cls.category_fifo.write(category_value)

        cls.account_expense_mp = get_account("601000")
        cls.account_valuation_mp = get_account("301000")
        cls.category_mp = cls.category_fifo.copy(
            {
                "property_account_expense_categ_id": cls.account_expense_mp.id,
                "property_stock_valuation_account_id": cls.account_valuation_mp.id,
            }
        )

        cls.price_p1 = 50.0
        cls.price_p2 = 50.0
        cls.list_price_p1 = 70.0
        cls.list_price_p2 = 70.0

        cls.product_mp = cls.env["product.product"].create(
            {
                "name": "Product MP",
                "is_storable": True,
                "categ_id": cls.category_mp.id,
                "invoice_policy": "delivery",
                "purchase_method": "receive",
                "list_price": cls.list_price_p1,
                "standard_price": cls.price_p1,
            }
        )

        warehouse = cls.company_data.get("default_warehouse")
        if not warehouse:
            warehouse = cls.env["stock.warehouse"].search(
                [("company_id", "=", cls.env.company.id)], limit=1
            )

        picking_type_in = warehouse.in_type_id
        location = picking_type_in.default_location_dest_id

        vals = {
            "name": "TEST warehouse",
            "location_id": location.id,
        }
        if "l10n_ro_merchandise_type" in cls.env["stock.location"]._fields:
            vals["l10n_ro_merchandise_type"] = "warehouse"

        cls.location_warehouse = location.copy(vals)

        picking_type_transfer = warehouse.int_type_id
        cls.picking_type_transfer = picking_type_transfer.copy(
            {
                "default_location_src_id": cls.location_warehouse.id,
                "default_location_dest_id": cls.location_warehouse.id,
                "name": "TEST Transfer",
                "sequence_code": "TR_test",
            }
        )

    def set_stock(self, product, qty):
        inventory_obj = self.env["stock.quant"].with_context(inventory_mode=True)
        inventory = inventory_obj.create(
            {
                "location_id": self.location_warehouse.id,
                "product_id": product.id,
                "inventory_quantity": qty,
            }
        )
        inventory._apply_inventory()

    def transfer(self, location, location_dest, product=None, accounting_date=False):
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
                "product_id": product.id,
                "product_uom_qty": 10,
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
        for move in picking.move_ids:
            move._set_quantity_done(move.product_uom_qty)

        return picking

    def test_transfer_backorder(self):
        self.set_stock(self.product_mp, 1000)
        acc_date = fields.Date.today() - timedelta(days=1)
        location_id = self.picking_type_transfer.default_location_src_id
        location_dest_id = self.picking_type_transfer.default_location_dest_id.copy(
            {"l10n_ro_property_stock_valuation_account_id": self.account_valuation.id}
        )
        _logger.info("Start transfer")
        picking = self.transfer(location_id, location_dest_id)
        picking.move_ids[0]._set_quantity_done(2)
        picking.move_ids[0].picked = True

        action_data = picking.button_validate()
        backorder_wizard = Form(
            self.env["stock.backorder.confirmation"].with_context(
                **action_data.get("context", {})
            )
        ).save()
        backorder_wizard.l10n_ro_accounting_date = acc_date
        backorder_wizard.process()
        stock_move = picking.move_ids
        _logger.info("Tranfer efectuat")
        self.assertEqual(picking.l10n_ro_accounting_date.date(), acc_date)
        self.assertEqual(stock_move.date.date(), acc_date)
        self.assertEqual(stock_move.move_line_ids.date.date(), acc_date)
        self.assertEqual(
            stock_move.stock_valuation_layer_ids.mapped("create_date")[0].date(),
            acc_date,
        )
        self.assertEqual(stock_move.account_move_ids.date, acc_date)

    def test_transfer_cancel_backorder(self):
        self.set_stock(self.product_mp, 1000)
        acc_date = fields.Date.today() - timedelta(days=1)
        location_id = self.picking_type_transfer.default_location_src_id
        location_dest_id = self.picking_type_transfer.default_location_dest_id.copy(
            {"l10n_ro_property_stock_valuation_account_id": self.account_valuation.id}
        )
        _logger.info("Start transfer")
        picking = self.transfer(location_id, location_dest_id)

        picking.move_ids[0]._set_quantity_done(2)
        picking.move_ids[0].picked = True

        action_data = picking.button_validate()
        backorder_wizard = Form(
            self.env["stock.backorder.confirmation"].with_context(
                **action_data.get("context", {})
            )
        ).save()
        backorder_wizard.l10n_ro_accounting_date = acc_date
        backorder_wizard.process_cancel_backorder()
        stock_move = picking.move_ids.filtered(lambda m: m.state == "done")
        _logger.info("Tranfer efectuat")
        self.assertEqual(picking.l10n_ro_accounting_date.date(), acc_date)
        self.assertEqual(stock_move.date.date(), acc_date)
        self.assertEqual(stock_move.move_line_ids.date.date(), acc_date)
        self.assertEqual(
            stock_move.stock_valuation_layer_ids.mapped("create_date")[0].date(),
            acc_date,
        )
        self.assertEqual(stock_move.account_move_ids.date, acc_date)

    def test_receipt(self):
        picking_type_in = self.picking_type_in_warehouse
        acc_date = fields.Date.today() - timedelta(days=1)
        po = Form(self.env["purchase.order"])
        po.partner_id = self.vendor
        po.picking_type_id = picking_type_in

        with po.order_line.new() as po_line:
            po_line.product_id = self.product_1
            po_line.product_qty = self.qty_po_p1
            po_line.price_unit = self.price_p1

        po = po.save()
        po.button_confirm()
        picking = po.picking_ids.filtered(lambda pick: pick.state != "done")
        picking.l10n_ro_accounting_date = acc_date

        # in 17.0 nu mai exista stock.immediate.transfer
        # wiz = picking.button_validate()
        # wiz = Form(
        #     self.env["stock.immediate.transfer"].with_context(**wiz["context"])
        # ).save()
        # wiz.l10n_ro_accounting_date = acc_date
        # wiz.process()
        for move in picking.move_ids:
            move._set_quantity_done(move.product_uom_qty)
            move.picked = True
        picking._action_done()

        stock_move = picking.move_ids
        _logger.info("Tranfer efectuat")
        self.assertEqual(picking.l10n_ro_accounting_date.date(), acc_date)
        self.assertEqual(stock_move.date.date(), acc_date)
        self.assertEqual(stock_move.move_line_ids.date.date(), acc_date)
        self.assertEqual(
            stock_move.stock_valuation_layer_ids.mapped("create_date")[0].date(),
            acc_date,
        )
