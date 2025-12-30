# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from datetime import timedelta

from odoo import fields
from odoo.tests import Form, tagged

from odoo.addons.l10n_ro_stock_account_date.tests.test_stock_accounting_date import (
    TestStockAccountDate,
)

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockAccountDateWizard(TestStockAccountDate):
    @TestStockAccountDate.setup_country("ro")
    def setUp(cls):
        super().setUp()

    def make_transfer(self):
        int_picking_type = self.location.warehouse_id.int_type_id
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": int_picking_type.id,
                "location_id": self.location.id,
                "location_dest_id": self.location1.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_fifo.id,
                            "product_uom_qty": 5,
                            "product_uom": self.product_fifo.uom_id.id,
                            "location_id": self.location.id,
                            "location_dest_id": self.location1.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids._set_quantity_done(2)
        return picking

    def test_transfer_backorder(self):
        self.make_purchase()
        picking = self.make_transfer()
        acc_date = fields.Date.today() - timedelta(days=1)

        action_data = picking.button_validate()
        backorder_wizard = Form(
            self.env["stock.backorder.confirmation"].with_context(
                **action_data.get("context", {})
            )
        ).save()
        backorder_wizard.l10n_ro_accounting_date = acc_date
        backorder_wizard.process()
        stock_move = picking.move_ids
        self.assertEqual(picking.l10n_ro_accounting_date.date(), acc_date)
        self.assertEqual(stock_move.date.date(), acc_date)
        self.assertEqual(
            any(
                move_line.date.date() == acc_date
                for move_line in stock_move.move_line_ids
            ),
            True,
        )
        self.assertTrue(stock_move.account_move_id)
        self.assertEqual(stock_move.account_move_id.date, acc_date)

    def test_transfer_cancel_backorder(self):
        self.make_purchase()
        picking = self.make_transfer()
        acc_date = fields.Date.today() - timedelta(days=1)

        action_data = picking.button_validate()
        backorder_wizard = Form(
            self.env["stock.backorder.confirmation"].with_context(
                **action_data.get("context", {})
            )
        ).save()
        backorder_wizard.l10n_ro_accounting_date = acc_date
        backorder_wizard.process_cancel_backorder()
        stock_move = picking.move_ids.filtered(lambda m: m.state == "done")
        self.assertEqual(picking.l10n_ro_accounting_date.date(), acc_date)
        self.assertEqual(stock_move.date.date(), acc_date)
        self.assertEqual(
            any(
                move_line.date.date() == acc_date
                for move_line in stock_move.move_line_ids
            ),
            True,
        )
        self.assertTrue(stock_move.account_move_id)
        self.assertEqual(stock_move.account_move_id.date, acc_date)
