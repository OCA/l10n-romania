# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile la achizitie
import logging

from odoo.tests import tagged

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockPurchaseReturn(TestStockCommon):
    def test_return_in_picking(self):
        self.create_po()
        # Create return picking
        pick = self.po.picking_ids

        self.make_return(pick, 2)
