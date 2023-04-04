# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile la achizitie
import logging

from odoo.tests import Form, tagged

from .common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockSale(TestStockCommon):
    def test_sale_and_invoice_standard(self):
        """
        Vanzare si facturare
             - initial in stoc si contabilitate este valoarea din achizitie
             - dupa vanzare valoarea stocului trebuie sa scada cu valoarea stocului
             vandut
             - valoarea din stoc trebuie sa fie egala cu valoarea din contabilitate
             - in contul de venituri trebuie sa fie inregistrata valoarea de vanzare
        Fara l10n_ro_accounting descarcarea de gestiune se face pe factura,
        anglo-saxon standard
        """

        self.env.company.l10n_ro_accounting = False

        #  intrare in stoc
        self.make_purchase()

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)
        self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        # iesire din stoc prin vanzare
        self.create_so()

        # valoarea de stoc dupa vanzarea produselor
        val_stock_p1 = round(self.val_p1_i - self.val_stock_out_so_p1, 2)
        val_stock_p2 = round(self.val_p2_i - self.val_stock_out_so_p2, 2)

        self.check_stock_valuation(val_stock_p1, val_stock_p2)

        self.create_sale_invoice()

        _logger.debug("Verifcare valoare ramas in stoc")
        self.check_stock_valuation(val_stock_p1, val_stock_p2)
        self.check_account_valuation(val_stock_p1, val_stock_p2)

        _logger.debug("Verifcare valoare vanduta")
        self.check_account_valuation(
            -self.val_so_p1, -self.val_so_p2, self.account_income
        )

    def test_sale_and_invoice(self):
        """
        Vanzare si facturare
             - initial in stoc si contabilitate este valoarea din achizitie
             - dupa vanzare valoarea stocului trebuie sa scada cu valoarea stocului
             vandut
             - valoarea din stoc trebuie sa fie egala cu valoarea din contabilitate
             - in contul de venituri trebuie sa fie inregistrata valoarea de vanzare
        """

        #  intrare in stoc
        self.make_purchase()

        self.check_stock_valuation(self.val_p1_i, self.val_p2_i)
        self.check_account_valuation(self.val_p1_i, self.val_p2_i)

        # iesire din stoc prin vanzare
        self.create_so()

        # valoarea de stoc dupa vanzarea produselor
        val_stock_p1 = round(self.val_p1_i - self.val_stock_out_so_p1, 2)
        val_stock_p2 = round(self.val_p2_i - self.val_stock_out_so_p2, 2)

        self.check_stock_valuation(val_stock_p1, val_stock_p2)
        self.check_account_valuation(val_stock_p1, val_stock_p2)

        self.create_sale_invoice()

        _logger.debug("Verifcare valoare ramas in stoc")
        self.check_stock_valuation(val_stock_p1, val_stock_p2)
        self.check_account_valuation(val_stock_p1, val_stock_p2)

        _logger.debug("Verifcare valoare vanduta")
        self.check_account_valuation(
            -self.val_so_p1, -self.val_so_p2, self.account_income
        )

    def test_sale_and_invoice_and_retur(self):
        """
        Vanzare si facturare
         - initial in stoc si contabilitate este valoarea din achizitie
         - dupa vanzare valoarea stocului trebuie sa scada cu valoarea stocului vandut
         - valoarea din stoc trebuie sa fie egala cu valoarea din contabilitate
         - in contul de venituri trebuie sa fie inregistrata valoarea de vanzare
        """

        #  intrare in stoc
        self.make_purchase()

        # iesire din stoc prin vanzare
        self.create_so()
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

        return_pick.button_validate()

        self.create_sale_invoice()

    def test_sale_average(self):
        self.product_1.product_tmpl_id.categ_id.property_cost_method = "average"
        self.product_2.product_tmpl_id.categ_id.property_cost_method = "average"

        # price p1 = 50, qty p1 = 10
        self.create_po()

        self.price_p1 = 60.0
        self.price_p2 = 60.0
        self.create_po()

        self.assertEqual(self.product_1.standard_price, 55)
        self.assertEqual(self.product_2.standard_price, 55)

        self.qty_so_p1 = 1.0
        self.create_so()

        # valoarea de stoc dupa vanzarea produselor
        val_stock_p1 = round(self.qty_po_p1 * 50 + self.qty_po_p1 * 60 - 1 * 55, 2)
        val_stock_p2 = round(
            self.qty_po_p2 * 50 + self.qty_po_p2 * 60 - self.qty_so_p2 * 55, 2
        )

        self.check_stock_valuation(val_stock_p1, val_stock_p2)
        self.check_account_valuation(-1 * 55, -self.qty_so_p2 * 55)

        # vanzare restul => stock = 0
        self.qty_so_p1 = 19
        self.qty_so_p2 = 15
        self.create_so()

        self.check_stock_valuation(0.0, 0.0)
        self.check_account_valuation(
            -1 * 2 * self.qty_po_p1 * 55, -1 * 2 * self.qty_po_p2 * 55
        )
