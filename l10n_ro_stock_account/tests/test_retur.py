# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile la achizitie
import logging

from odoo.tests import Form

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


class TestStockPurchaseReturn(TestStockCommon):
    def test_return_in_picking(self):
        self.create_po()
        # Create return picking
        pick = self.po.picking_ids

        self.make_return(pick, 2)

    def test_return_in_notice_picking(self):
        self.create_po(notice=True)
        _logger.info("Start generare retur")
        # Create return picking
        pick = self.po.picking_ids

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=pick.ids, active_id=pick.ids[0], active_model="stock.picking"
            )
        )
        return_wiz = stock_return_picking_form.save()
        return_wiz.product_return_moves.write(
            {"quantity": 2.0, "to_refund": True}
        )  # Return only 2
        res = return_wiz.create_returns()
        return_pick = self.env["stock.picking"].browse(res["res_id"])

        # Validate picking
        return_pick.move_line_ids.write({"qty_done": 2})
        return_pick.notice = True  # asta trebuia sa fie setat in mod automat
        return_pick.button_validate()
