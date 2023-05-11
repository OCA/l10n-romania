# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from datetime import timedelta

from odoo import fields
from odoo.tests import Form, tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockReport(TestStockCommon):
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
                "name": product.name,
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
        for move_line in picking.move_ids:
            if move_line.product_uom_qty > 0 and move_line.quantity_done == 0:
                move_line.write({"quantity_done": move_line.product_uom_qty})
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
        picking.move_ids[0].move_line_ids[0].qty_done = 2
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
        picking.move_ids[0].move_line_ids[0].qty_done = 2
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

        wiz = picking.button_validate()
        wiz = Form(
            self.env["stock.immediate.transfer"].with_context(**wiz["context"])
        ).save()
        wiz.l10n_ro_accounting_date = acc_date
        wiz.process()

        stock_move = picking.move_ids
        _logger.info("Tranfer efectuat")
        self.assertEqual(picking.l10n_ro_accounting_date.date(), acc_date)
        self.assertEqual(stock_move.date.date(), acc_date)
        self.assertEqual(stock_move.move_line_ids.date.date(), acc_date)
        self.assertEqual(
            stock_move.stock_valuation_layer_ids.mapped("create_date")[0].date(),
            acc_date,
        )
