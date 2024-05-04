# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile la achizitie
import logging

from odoo.tests import Form, tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockPurchaseReturn(TestStockCommon):
    def test_return_in_notice_picking(self):
        self.create_po(vals={"l10n_ro_notice": True})
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
        for move in return_pick.move_ids:
            move._set_quantity_done(move.product_uom_qty)
        return_pick.l10n_ro_notice = True  # asta trebuia sa fie setat in mod automat
        return_pick.button_validate()
