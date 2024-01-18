# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile la achizitie
import logging

from odoo.tests import Form, tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockSale(TestStockCommon):
    def test_sale_notice_and_invoice(self):
        """
        - initial in stoc si contabilitate este valoarea din achizitie
        - dupa vanzare valoarea stocului trebuie sa scada cu valoarea stocului
        vandut
        - valoarea din stoc trebuie sa fie egala cu valoarea din contabilitate
        - in contul de venituri trebuie sa fie inregistrata valoarea de vanzare
        """

        self.make_purchase()

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)
        self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        self.create_so(vals={"l10n_ro_notice": True})

        # valoarea de stoc dupa vanzarea produselor
        val_stock_p1 = round(self.val_p1_i - self.val_stock_out_so_p1, 2)
        val_stock_p2 = round(self.val_p2_i - self.val_stock_out_so_p2, 2)

        self.check_stock_valuation(val_stock_p1, val_stock_p2)

        # inca nu se face si descaracarea contabila de gestiune!
        self.check_account_valuation(val_stock_p1, val_stock_p2)

        self.create_sale_invoice()

        _logger.info("Verifcare valoare ramas in stoc")
        self.check_stock_valuation(val_stock_p1, val_stock_p2)
        self.check_account_valuation(val_stock_p1, val_stock_p2)

        _logger.info("Verifcare valoare vanduta")
        self.check_account_valuation(
            -self.val_so_p1, -self.val_so_p2, self.account_income
        )

    def test_sale_notice_and_invoice_and_retur(self):
        """
        Vanzare si facturare
         - initial in stoc si contabilitate este valoarea din achizitie
         - dupa livrare valoarea stocului trebuie sa scada cu valoarea stocului vandut
         - trebuie sa se inregistreze in contul 418 valoare de vanzare
         - valoarea din stoc trebuie sa fie egala cu valoarea din contabilitate
         - in contul de venituri trebuie sa fie inregistrata valoarea de vanzare
         - dupa facturare soldul contului 418 trebuie sa fie zero
        """

        #  intrare in stoc
        self.make_purchase()

        # iesire din stoc prin vanzare
        self.create_so(vals={"l10n_ro_notice": True})
        pick = self.so.picking_ids

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
        return_pick.l10n_ro_notice = True
        return_pick.button_validate()

        self.create_sale_invoice()
