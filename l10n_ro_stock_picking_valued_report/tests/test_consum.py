# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged

from .common import TestStockPickingValued

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockConsumn(TestStockPickingValued):
    def test_transfer(self):
        self.set_stock(self.product_mp, 1000)
        location_id = self.picking_type_transfer.default_location_src_id
        location_dest_id = self.picking_type_transfer.default_location_dest_id
        _logger.info("Start transfer")
        self.transfer(location_id, location_dest_id)
        picking = self.picking
        _logger.info("Tranfer efectuat")
        self.assertEqual(picking.l10n_ro_amount_untaxed, 100.0)
        self.assertEqual(picking.l10n_ro_amount_tax, 0.0)
        self.assertEqual(picking.l10n_ro_amount_total, 100.0)
        self.assertEqual(picking.move_line_ids.l10n_ro_price_subtotal, 100.0)
        self.assertEqual(picking.move_line_ids.l10n_ro_price_tax, 0.0)
        self.assertEqual(picking.move_line_ids.l10n_ro_price_total, 100.0)

    def test_consume(self):
        self.set_stock(self.product_mp, 1000)
        _logger.info("Start consum produse")
        location_id = self.picking_type_transfer.default_location_src_id
        location_dest_id = self.picking_type_transfer.default_location_dest_id.copy(
            {"usage": "consume"}
        )
        self.transfer(location_id, location_dest_id)
        picking = self.picking
        _logger.info("Consum facuta")
        self.assertEqual(picking.l10n_ro_amount_untaxed, 100.0)
        self.assertEqual(picking.l10n_ro_amount_tax, 0.0)
        self.assertEqual(picking.l10n_ro_amount_total, 100.0)
        self.assertEqual(picking.move_line_ids.l10n_ro_price_subtotal, 100.0)
        self.assertEqual(picking.move_line_ids.l10n_ro_price_tax, 0.0)
        self.assertEqual(picking.move_line_ids.l10n_ro_price_total, 100.0)
